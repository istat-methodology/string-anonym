"""Esporta input e annotazioni separati per lo sviluppo del masking, senza API."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

TIPI = {'PERSON', 'ADDRESS', 'EMAIL', 'PHONE', 'COD_UTENTE', 'PASSWORD', 'NUM_PRATICA'}


def leggi(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def converti(record, identificativo):
    chat = record['chat']
    messaggi = chat['conversazione']
    if not isinstance(messaggi, list) or not messaggi:
        raise ValueError('Conversazione vuota o non valida')
    puliti = []
    for i, m in enumerate(messaggi):
        if m['sender'] not in {'Utente', 'Agente'} or not isinstance(m['testo'], str) or not m['testo'].strip():
            raise ValueError('Messaggio non valido')
        puliti.append({'sender': m['sender'], 'testo': m['testo']})
    spans = []
    omessi = 0
    occupati = {}
    for a in chat['trattamento_atteso']['mascherare']:
        match = re.fullmatch(r'conversazione\.(\d+)\.testo', a['campo'])
        if not match:
            if a['campo'] == 'metadati.descrizione' or a['campo'].startswith('trattamento_atteso.'):
                omessi += 1
                continue
            raise ValueError('Campo annotazione sconosciuto')
        i = int(match[1])
        start, end = a['start'], a['end']
        if i >= len(puliti) or type(start) is not int or type(end) is not int:
            raise ValueError('Posizioni non valide')
        testo = puliti[i]['testo']
        if not 0 <= start < end <= len(testo) or testo[start:end] != a['testo'] or a['tipo'] not in TIPI:
            raise ValueError('Span non coerente con il testo o tipo non supportato')
        if any(start < b and end > x for x, b in occupati.get(i, [])):
            raise ValueError('Span sovrapposti')
        occupati.setdefault(i, []).append((start, end))
        spans.append({k: a[k] for k in ('campo', 'start', 'end', 'tipo', 'id_entita', 'id_forma', 'testo', 'sostituzione')})
    return ({'id': identificativo, 'conversazione': puliti},
            {'id': identificativo, 'annotazioni': spans}, omessi)


def esporta(fonti, destinazione, revisioni=()):
    if destinazione.exists():
        raise ValueError('La cartella di destinazione deve essere nuova')
    inputs, gold, provenienza, esclusi = [], [], [], []
    hashes, ids, fonti_manifest = set(), set(), []
    categorie = Counter()
    omessi = 0
    rapporti = {}
    for path in revisioni:
        rapporto = json.loads(path.read_text(encoding='utf-8'))
        digest = rapporto['sha256']
        if digest in rapporti:
            raise ValueError('Più revisioni per la stessa fonte')
        rapporti[digest] = rapporto
    for path in fonti:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in hashes:
            raise ValueError('Fonte duplicata')
        hashes.add(digest)
        fonti_manifest.append({'path': str(path.resolve()), 'sha256': digest})
        rapporto = rapporti.get(digest)
        note = {}
        if rapporto:
            for s in rapporto['segnalazioni']:
                note.setdefault(s['id'], []).append(s['osservazione'])
        for numero, r in enumerate(leggi(path), 1):
            originale = r['id']
            identificativo = digest + ':' + originale
            if identificativo in ids:
                raise ValueError('ID duplicato nella fonte')
            ids.add(identificativo)
            traccia = {'id': identificativo, 'id_originale': originale, 'fonte_sha256': digest,
                       'record': numero, 'stato_validazione': r.get('stato'),
                       'revisione_qualitativa': 'segnalato' if originale in note else 'non_revisionato',
                       'osservazioni': note.get(originale, [])}
            if r.get('stato') != 'valido':
                esclusi.append({**traccia, 'motivo': r.get('errore') or 'Validazione non superata'})
                continue
            try:
                inp, atteso, fuori_dialogo = converti(r, identificativo)
            except (ValueError, KeyError, TypeError, IndexError) as error:
                esclusi.append({**traccia, 'motivo': str(error)})
                continue
            inputs.append(inp)
            gold.append(atteso)
            provenienza.append(traccia)
            categorie.update(a['tipo'] for a in atteso['annotazioni'])
            omessi += fuori_dialogo
    if set(rapporti) - hashes:
        raise ValueError('Una revisione non corrisponde agli hash delle fonti indicate')
    manifest = {'versione': '1.0', 'uso': 'sviluppo; non test finale né gold approvato',
                'fonti': fonti_manifest, 'revisioni': [rapporti[h] for h in sorted(rapporti)],
                'record_letti': len(ids), 'esportati': len(inputs), 'esclusi': len(esclusi),
                'categorie': dict(categorie), 'annotazioni_fuori_dialogo_omesse': omessi,
                'revisione_qualitativa': dict(Counter(p['revisione_qualitativa'] for p in provenienza)),
                'contesto': 'Per ogni messaggio usare solo i turni precedenti, mai quelli futuri.',
                'input_modello': 'Solo conversazione: testi e ruoli; id è una chiave tecnica, non una feature.'}
    destinazione.mkdir(parents=True, exist_ok=False)
    for nome, righe in [('input.jsonl', inputs), ('annotazioni_attese.jsonl', gold),
                         ('provenienza.jsonl', provenienza), ('esclusi.jsonl', esclusi)]:
        with (destinazione / nome).open('x', encoding='utf-8') as f:
            for riga in righe:
                f.write(json.dumps(riga, ensure_ascii=False) + '\n')
    (destinazione / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revisione', type=Path, action='append', default=[])
    args = parser.parse_args()
    try:
        risultato = esporta(args.input, args.output, args.revisione)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps({k: risultato[k] for k in ('record_letti', 'esportati', 'esclusi', 'categorie', 'revisione_qualitativa')}, ensure_ascii=False))
    print(f'Salvato in: {args.output}')


if __name__ == '__main__':
    main()
