"""Lotto pilota OpenAI: riusa risposte compatibili e genera solo le schede mancanti."""

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

from genera_chat import ROOT, ENDPOINT, parametri_richiesta


def leggi(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def salva(path, records):
    with path.open('x', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')


def riepilogo_esistente(cartella, prompts, deployment):
    """Legge risultati salvati, senza considerarli richieste da rieseguire."""
    finale = cartella / 'chat_lotto.jsonl'
    if not finale.exists():
        return 'Cartella già esistente, senza risultato finale: lotto da verificare. Nessuna ripresa automatica.'
    previsti = {p['id']: p for p in prompts}
    if len(previsti) != len(prompts) or not prompts:
        raise ValueError('Lotto vuoto o ID duplicati nei prompt')
    records = leggi(finale)
    visti = set()
    for record in records:
        identificativo = record['id']
        if (identificativo in visti or identificativo not in previsti or
                record.get('prompt') != previsti[identificativo] or
                record.get('deployment') != deployment or record.get('provider') != 'openai'):
            raise ValueError('Risultati esistenti non compatibili con la configurazione o ID duplicati')
        visti.add(identificativo)
    stati = Counter(r['stato'] for r in records)
    if set(stati) - {'valido', 'da_verificare', 'errore_api'}:
        raise ValueError('Stato non riconosciuto nei risultati esistenti')
    riepilogo = (f"Risposte presenti: {len(records)}/{len(prompts)}; "
                 f"valide: {stati['valido']}; da verificare: {stati['da_verificare']}; "
                 f"errori API: {stati['errore_api']}.")
    if len(records) != len(prompts) or stati['errore_api']:
        riepilogo += ' Lotto incompleto o con errori: verificare gli esiti. Nessuna ripresa automatica.'
    return riepilogo


def seleziona(prompts, precedenti, deployment, endpoint, max_tokens):
    per_id = {p['id']: p for p in prompts}
    if not prompts or len(per_id) != len(prompts):
        raise ValueError('Lotto vuoto o ID duplicati nei prompt')
    riusati = {}
    fonti = {}
    for fonte, record in precedenti:
        prompt = per_id.get(record.get('id'))
        if (prompt is None or record.get('prompt') != prompt or
                record.get('provider') != 'openai' or record.get('deployment') != deployment or
                record.get('endpoint', '').rstrip('/') != endpoint.rstrip('/') or
                record.get('parametri_api') != parametri_richiesta(prompt, deployment, max_tokens, 'openai')):
            continue
        # Non ripetere automaticamente richieste fallite o dall'esito incerto.
        if record.get('stato') == 'errore_api' or not record.get('risposta_originale'):
            raise ValueError(f"Esito API incerto per {record['id']} in {fonte}: verificare prima di riprovare")
        if record.get('stato') not in {'valido', 'da_verificare'}:
            raise ValueError(f"Stato non riconosciuto in {fonte}")
        if record['id'] in riusati and riusati[record['id']] != record:
            raise ValueError(f"Più risposte compatibili per {record['id']}: selezionare i file con --riusa")
        riusati[record['id']] = record
        fonti[record['id']] = str(fonte)
    return [p for p in prompts if p['id'] not in riusati], riusati, fonti


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'output/prompts_v4_1.jsonl')
    parser.add_argument('--riusa', type=Path, action='append', help='Output precedente da confrontare; ripetibile. Default: test_openai*.jsonl accanto ai prompt')
    parser.add_argument('--cartella-output', type=Path, default=ROOT / 'output/lotto_openai_v4_1')
    parser.add_argument('--deployment', default='gpt-5.6-terra')
    parser.add_argument('--endpoint', default=ENDPOINT)
    parser.add_argument('--max-output-tokens', type=int, default=6000)
    parser.add_argument('--solo-controllo', action='store_true', help='Mostra il piano senza scrivere file né chiamare API')
    args = parser.parse_args()
    try:
        if args.max_output_tokens < 1:
            raise ValueError('Il limite di token deve essere positivo')
        prompts = leggi(args.input)
        if args.cartella_output.exists():
            if args.solo_controllo:
                print(riepilogo_esistente(args.cartella_output, prompts, args.deployment))
                return
            raise ValueError('Cartella output già esistente: usare --solo-controllo per verificarne gli esiti')
        files = args.riusa if args.riusa is not None else sorted(args.input.parent.glob('test_openai*.jsonl'))
        precedenti = [(path, r) for path in files for r in leggi(path)]
        mancanti, riusati, fonti = seleziona(prompts, precedenti, args.deployment, args.endpoint, args.max_output_tokens)
        print(f'Schede: {len(prompts)}; riutilizzate: {len(riusati)}; nuove chiamate: {len(mancanti)}', flush=True)
        if args.solo_controllo:
            return
        # Una cartella nuova impedisce rilanci accidentali dopo interruzioni.
        args.cartella_output.mkdir(parents=True, exist_ok=False)
        pending = args.cartella_output / 'prompts_mancanti.jsonl'
        nuove = args.cartella_output / 'chat_nuove.jsonl'
        salva(pending, mancanti)
        salva(args.cartella_output / 'chat_riutilizzate.jsonl', [riusati[p['id']] for p in prompts if p['id'] in riusati])
        piano = {'input':str(args.input), 'deployment':args.deployment, 'endpoint':args.endpoint,
                 'max_output_tokens':args.max_output_tokens, 'fonti_riutilizzate':fonti,
                 'id_previsti':[p['id'] for p in prompts], 'id_da_generare':[p['id'] for p in mancanti]}
        with (args.cartella_output / 'piano.json').open('x', encoding='utf-8') as f:
            json.dump(piano, f, ensure_ascii=False, indent=2)
        codice = 0
        if mancanti:
            comando = [sys.executable, str(ROOT / 'src/genera_chat.py'), '--input', str(pending),
                       '--output', str(nuove), '--provider', 'openai', '--deployment', args.deployment,
                       '--endpoint', args.endpoint, '--max-output-tokens', str(args.max_output_tokens),
                       '--max-conversazioni', str(len(mancanti))]
            codice = subprocess.run(comando, check=False).returncode
        raccolti = dict(riusati)
        for record in leggi(nuove) if nuove.exists() else []:
            if record['id'] in raccolti:
                raise ValueError(f"Risposta duplicata: {record['id']}")
            raccolti[record['id']] = record
        records = [raccolti[p['id']] for p in prompts if p['id'] in raccolti]
        finale = args.cartella_output / 'chat_lotto.jsonl'
        salva(finale, records)
        stati = dict(Counter(r['stato'] for r in records))
        print(f'Salvati {len(records)}/{len(prompts)} risultati in {finale}; stati: {stati}')
        if codice or len(records) != len(prompts):
            print('Lotto da controllare: nessun retry automatico. Conservare la cartella prima di riprendere.')
            raise SystemExit(1)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
