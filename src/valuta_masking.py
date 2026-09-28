"""Confronta predizioni e annotazioni attese. Non carica modelli né chiama API."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from esporta_dataset_masking import leggi, TIPI


def indicizza(records):
    result = {}
    for r in records:
        if not isinstance(r.get('id'), str) or not r['id'] or r['id'] in result:
            raise ValueError('ID assente, non valido o duplicato')
        result[r['id']] = r
    return result


def span_validi(annotazioni, conversazione):
    if not isinstance(annotazioni, list):
        raise ValueError('annotazioni deve essere una lista')
    result = set()
    for a in annotazioni:
        match = re.fullmatch(r'conversazione\.(\d+)\.testo', a['campo'])
        if not match or a['tipo'] not in TIPI:
            raise ValueError('Campo o tipo non supportato')
        i = int(match[1])
        start, end = a['start'], a['end']
        if i >= len(conversazione) or type(start) is not int or type(end) is not int:
            raise ValueError('Posizioni non valide')
        testo = conversazione[i]['testo']
        if not 0 <= start < end <= len(testo):
            raise ValueError('Span fuori dal testo')
        if 'testo' in a and a['testo'] != testo[start:end]:
            raise ValueError('Testo dello span incoerente')
        item = (i, start, end, a['tipo'])
        if any(i == j and start < b and end > x for j, x, b, _ in result):
            raise ValueError('Span duplicati o sovrapposti')
        result.add(item)
    return result


def caratteri(spans):
    return {(i, p) for i, start, end, _ in spans for p in range(start, end)}


def metriche(tp, fp, fn):
    return {'tp': tp, 'fp': fp, 'fn': fn,
            'precision': tp / (tp + fp) if tp + fp else None,
            'recall': tp / (tp + fn) if tp + fn else None,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def valuta(inputs, attese, predizioni):
    inputs, attese, predizioni = map(indicizza, (inputs, attese, predizioni))
    if not inputs or inputs.keys() != attese.keys():
        raise ValueError('Input e annotazioni attese devono avere gli stessi ID e non essere vuoti')
    if predizioni.keys() - inputs.keys():
        raise ValueError('Predizioni con ID estranei al dataset')
    conteggi = Counter(); tipi = {t: Counter() for t in sorted(TIPI)}
    ruoli = {r: Counter() for r in ('Utente', 'Agente')}
    dettagli = []; tecnici = []; char_counts = Counter()
    for id_, inp in inputs.items():
        conv = inp['conversazione']
        if not conv or any(m['sender'] not in ruoli or not isinstance(m['testo'], str) for m in conv):
            raise ValueError('Input conversazione non valido')
        gold = span_validi(attese[id_]['annotazioni'], conv)
        pred = predizioni.get(id_)
        if pred is None:
            tecnici.append({'id': id_, 'stato': 'mancante'})
            continue
        if pred.get('stato') == 'errore':
            if not isinstance(pred.get('errore'), str) or not pred['errore'].strip() or pred.get('annotazioni'):
                raise ValueError('Errore tecnico senza motivo o con annotazioni ambigue')
            tecnici.append({'id': id_, 'stato': 'errore', 'errore': pred['errore']})
            continue
        if pred.get('stato') != 'ok':
            raise ValueError('Ogni predizione deve dichiarare stato ok oppure errore')
        spans = span_validi(pred['annotazioni'], conv)
        tp, fp, fn = gold & spans, spans - gold, gold - spans
        for nome, insieme in [('tp', tp), ('fp', fp), ('fn', fn)]:
            conteggi[nome] += len(insieme)
            for i, _, _, tipo in insieme:
                tipi[tipo][nome] += 1
                ruoli[conv[i]['sender']][nome] += 1
        gchars, pchars = caratteri(gold), caratteri(spans)
        char_counts.update({'sensibili_attesi': len(gchars), 'sensibili_coperti': len(gchars & pchars),
                            'sensibili_scoperti': len(gchars - pchars),
                            'non_sensibili_mascherati': len(pchars - gchars),
                            'non_sensibili_totali': sum(len(m['testo']) for m in conv) - len(gchars)})
        conteggi['valutate'] += 1
        conteggi['con_omissioni_caratteri'] += bool(gchars - pchars)
        conteggi['con_dati_attesi'] += bool(gold)
        conteggi['negative'] += not bool(gold)
        conteggi['negative_con_fp'] += not gold and bool(spans)
        if fp or fn:
            dettagli.append({'id': id_, 'fp': sorted(fp), 'fn': sorted(fn)})
    def riassumi(c):
        return metriche(c['tp'], c['fp'], c['fn'])
    return {'versione': '1.0', 'conversazioni_totali': len(inputs),
            'conversazioni_valutate': conteggi['valutate'], 'fallimenti_tecnici': tecnici,
            'nota': 'Metriche sui soli esiti ok; fallimenti e predizioni mancanti esclusi e riportati separatamente. Annotazioni attese non necessariamente revisionate.',
            'span_esatti_micro': riassumi(conteggi),
            'per_tipo': {k: riassumi(v) for k, v in tipi.items()},
            'per_ruolo': {k: riassumi(v) for k, v in ruoli.items()},
            'caratteri': {**char_counts,
                'recall_copertura': char_counts['sensibili_coperti']/char_counts['sensibili_attesi'] if char_counts['sensibili_attesi'] else None},
            'conversazioni_con_omissioni_caratteri': conteggi['con_omissioni_caratteri'],
            'conversazioni_con_dati_attesi_valutate': conteggi['con_dati_attesi'],
            'negative_valutate': conteggi['negative'], 'negative_con_falsi_positivi': conteggi['negative_con_fp'],
            'errori_span': dettagli}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--attese', type=Path, required=True)
    parser.add_argument('--predizioni', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError('Output già esistente')
        result = valuta(leggi(args.input), leggi(args.attese), leggi(args.predizioni))
        result['fonti'] = {k: {'path': str(p.resolve()), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                          for k, p in [('input', args.input), ('attese', args.attese), ('predizioni', args.predizioni)]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write('\n')
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps({k: result[k] for k in ('conversazioni_totali', 'conversazioni_valutate', 'span_esatti_micro')}, ensure_ascii=False))
    print(f"Fallimenti tecnici o mancanti: {len(result['fallimenti_tecnici'])}; report: {args.output}")


if __name__ == '__main__':
    main()
