"""Baseline regex: produce span, senza alterare testi e senza leggere il gold."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from detection import DETECTION_TYPES, merge_detection
from esporta_dataset_masking import leggi, TIPI
from valuta_masking import indicizza

ROOT = Path(__file__).resolve().parents[1]


def carica_regole(path):
    config = json.loads(path.read_text(encoding='utf-8'))
    nomi = set()
    for r in config['regole']:
        if r['nome'] in nomi or r['tipo'] not in DETECTION_TYPES or type(r['priorita']) is not int:
            raise ValueError('Regola duplicata o non valida')
        nomi.add(r['nome'])
        r['regex'] = re.compile(r['pattern'], re.IGNORECASE)
        if 'valore' not in r['regex'].groupindex:
            raise ValueError('Ogni regola deve avere il gruppo valore')
    return config


def riconosci(testo, regole):
    candidati = []
    for r in regole:
        for m in r['regex'].finditer(testo):
            start, end = m.span('valore')
            if start < 0 or end <= start:
                raise ValueError('Regola con span vuoto')
            candidati.append({'start': start, 'end': end, 'tipo': r['tipo'],
                              'testo': testo[start:end], 'regola': r['nome'], 'priorita': r['priorita']})
    scelti = []
    for a in sorted(candidati, key=lambda a: (-a['priorita'], -(a['end']-a['start']), a['start'], a['regola'])):
        if not any(a['start'] < b['end'] and a['end'] > b['start'] for b in scelti):
            scelti.append(a)
    return sorted(scelti, key=lambda a: a['start'])


def detect_regex(testo, regole, campo):
    """Produce tutte le detection regex sul testo originale, senza risolvere conflitti."""
    detections = []
    for rule in regole:
        for match in rule['regex'].finditer(testo):
            start, end = match.span('valore')
            if start < 0 or end <= start:
                raise ValueError('Regola con span vuoto')
            detections.append({
                'field': campo,
                'start': start,
                'end': end,
                'text': testo[start:end],
                'type': rule['tipo'],
                'sources': [{
                    'detector': 'regex',
                    'rule': rule['nome'],
                    'priority': rule['priorita'],
                }],
            })
    return detections


def predici(record, config):
    try:
        conv = record['conversazione']
        if not isinstance(conv, list) or not conv:
            raise ValueError('Conversazione vuota o non valida')
        spans = []
        raw_detections = []
        fields = {}
        for i, m in enumerate(conv):
            if m['sender'] not in {'Utente', 'Agente'} or not isinstance(m['testo'], str):
                raise ValueError('Messaggio non valido')
            campo = f'conversazione.{i}.testo'
            fields[campo] = m['testo']
            raw_detections.extend(detect_regex(m['testo'], config['regole'], campo))
            for a in riconosci(m['testo'], config['regole']):
                if a['tipo'] in TIPI:
                    spans.append({'campo': f'conversazione.{i}.testo', **a})
        detections = merge_detection(raw_detections, fields, record['id'])
        return {'id': record['id'], 'stato': 'ok', 'detections': detections,
                'annotazioni': spans, 'versione_regole': config['versione']}
    except (ValueError, KeyError, TypeError) as error:
        return {'id': record['id'], 'stato': 'errore', 'errore': str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Nuova cartella per predizioni e manifest')
    parser.add_argument('--regole', type=Path, default=ROOT/'config/regole_masking.json')
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError('La cartella output deve essere nuova')
        config = carica_regole(args.regole)
        records = list(indicizza(leggi(args.input)).values())
        if not records:
            raise ValueError('Input vuoto')
        risultati = [predici(r, config) for r in records]
        stati = dict(Counter(r['stato'] for r in risultati))
        manifest = {'sistema': 'regex', 'versione': config['versione'], 'stati': stati,
                    'fonti': {k: {'path': str(p.resolve()), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                              for k,p in [('input',args.input),('regole',args.regole)]}}
        args.output.mkdir(parents=True, exist_ok=False)
        with (args.output/'predizioni.jsonl').open('x', encoding='utf-8') as f:
            for r in risultati:
                f.write(json.dumps(r, ensure_ascii=False)+'\n')
        (args.output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    except (ValueError, OSError, KeyError, TypeError, re.error) as error:
        parser.error(str(error))
    print(f'Conversazioni: {len(risultati)}; stati: {stati}')
    print(f"Predizioni: {args.output/'predizioni.jsonl'}")
    if stati.get('errore'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
