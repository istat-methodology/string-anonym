"""Genera le conversazioni via OpenAI, riusando soltanto risposte compatibili."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from genera_chat import ROOT, ENDPOINT, parametri_richiesta


def leggi(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def salva(path, records):
    with path.open('x', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')


def salva_sostituendo(path, records):
    """Sostituisce un riepilogo in modo atomico senza lasciare file parziali."""
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                     prefix='.conversazioni-', suffix='.tmp', delete=False) as f:
        temporaneo = Path(f.name)
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    os.replace(temporaneo, path)


def riepilogo_esistente(cartella, prompts, deployment):
    """Legge risultati salvati, senza considerarli richieste da rieseguire."""
    finale = cartella / 'conversazioni.jsonl'
    if not finale.exists():
        return 'Cartella già esistente, senza risultato finale: generazione da verificare. Nessuna ripresa automatica.'
    previsti = {p['id']: p for p in prompts}
    if len(previsti) != len(prompts) or not prompts:
        raise ValueError('Elenco dei prompt vuoto o con ID duplicati')
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
        riepilogo += ' Generazione incompleta o con errori: verificare gli esiti. Nessuna ripresa automatica.'
    return riepilogo


def seleziona(prompts, precedenti, deployment, endpoint, max_tokens, ignora_errori_api=False):
    per_id = {p['id']: p for p in prompts}
    if not prompts or len(per_id) != len(prompts):
        raise ValueError('Elenco dei prompt vuoto o con ID duplicati')
    riusati = {}
    fonti = {}
    for fonte, record in precedenti:
        prompt = per_id.get(record.get('id'))
        if (prompt is None or record.get('prompt') != prompt or
                record.get('provider') != 'openai' or record.get('deployment') != deployment or
                record.get('endpoint', '').rstrip('/') != endpoint.rstrip('/') or
                record.get('parametri_api') != parametri_richiesta(prompt, deployment, max_tokens, 'openai')):
            continue
        if record.get('stato') == 'errore_api' and ignora_errori_api:
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


def verifica_piano_ripresa(cartella, prompts, input_path, deployment, endpoint, max_tokens):
    path = cartella / 'piano.json'
    if not path.is_file():
        raise ValueError('Cartella incompleta: manca piano.json; impossibile riprendere in sicurezza')
    piano = json.loads(path.read_text(encoding='utf-8'))
    atteso = {
        'input': str(input_path), 'deployment': deployment, 'endpoint': endpoint,
        'max_output_tokens': max_tokens, 'id_previsti': [p['id'] for p in prompts],
    }
    for campo, valore in atteso.items():
        corrente = piano.get(campo)
        if campo == 'endpoint' and isinstance(corrente, str):
            corrente, valore = corrente.rstrip('/'), valore.rstrip('/')
        if corrente != valore:
            raise ValueError(f'La ripresa non corrisponde al piano originale: {campo}')


def prossimo_segmento(cartella):
    indice = 1
    while (cartella / f'chat_ripresa_{indice:03d}.jsonl').exists() or (cartella / f'prompts_ripresa_{indice:03d}.jsonl').exists():
        indice += 1
    return (cartella / f'prompts_ripresa_{indice:03d}.jsonl',
            cartella / f'chat_ripresa_{indice:03d}.jsonl')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'output/prompts_paper_300.jsonl')
    parser.add_argument('--riusa', type=Path, action='append', help='Output precedente da confrontare; ripetibile. Default: test_openai*.jsonl accanto ai prompt')
    parser.add_argument('--cartella-output', type=Path, default=ROOT / 'output/generazione_paper_300')
    parser.add_argument('--deployment', default='gpt-5.6-terra')
    parser.add_argument('--endpoint', default=ENDPOINT)
    parser.add_argument('--max-output-tokens', type=int, default=6000)
    parser.add_argument('--solo-controllo', action='store_true', help='Mostra il piano senza scrivere file né chiamare API')
    parser.add_argument('--riprendi', action='store_true', help='Continua una generazione interrotta senza ripetere le chiamate riuscite')
    args = parser.parse_args()
    try:
        if args.max_output_tokens < 1:
            raise ValueError('Il limite di token deve essere positivo')
        prompts = leggi(args.input)
        if args.solo_controllo and args.riprendi:
            raise ValueError('--solo-controllo e --riprendi non possono essere usati insieme')
        esistente = args.cartella_output.exists()
        if esistente:
            if args.solo_controllo:
                print(riepilogo_esistente(args.cartella_output, prompts, args.deployment))
                return
            if not args.riprendi:
                raise ValueError('Cartella output già esistente: usare la fase riprendi per continuare senza duplicati')
            verifica_piano_ripresa(args.cartella_output, prompts, args.input, args.deployment,
                                   args.endpoint, args.max_output_tokens)
        elif args.riprendi:
            raise ValueError('Cartella output assente: usare genera per iniziare una nuova generazione')
        if esistente:
            files = ([args.cartella_output / 'chat_riutilizzate.jsonl',
                      args.cartella_output / 'chat_nuove.jsonl'] +
                     sorted(args.cartella_output.glob('chat_ripresa_*.jsonl')))
            files = [path for path in files if path.is_file()]
        else:
            files = args.riusa if args.riusa is not None else sorted(args.input.parent.glob('test_openai*.jsonl'))
        precedenti = [(path, r) for path in files for r in leggi(path)]
        mancanti, riusati, fonti = seleziona(prompts, precedenti, args.deployment, args.endpoint,
                                             args.max_output_tokens, ignora_errori_api=args.riprendi)
        print(f'Schede: {len(prompts)}; riutilizzate: {len(riusati)}; nuove chiamate: {len(mancanti)}', flush=True)
        if args.solo_controllo:
            return
        if esistente:
            pending, nuove = prossimo_segmento(args.cartella_output)
        else:
            # Una cartella nuova impedisce rilanci accidentali dopo interruzioni.
            args.cartella_output.mkdir(parents=True, exist_ok=False)
            pending = args.cartella_output / 'prompts_mancanti.jsonl'
            nuove = args.cartella_output / 'chat_nuove.jsonl'
        salva(pending, mancanti)
        if not esistente:
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
                       '--max-conversazioni', str(len(mancanti)),
                       '--progresso-iniziale', str(len(riusati)),
                       '--progresso-totale', str(len(prompts))]
            codice = subprocess.run(comando, check=False).returncode
        tutti = precedenti + [(nuove, r) for r in leggi(nuove)] if nuove.exists() else precedenti
        ultimi = {}
        for _, record in tutti:
            ultimi[record['id']] = record
        ultimi.update(riusati)  # una risposta utilizzabile prevale su un errore API successivo
        records = [ultimi[p['id']] for p in prompts if p['id'] in ultimi]
        finale = args.cartella_output / 'conversazioni.jsonl'
        if esistente:
            salva_sostituendo(finale, records)
        else:
            salva(finale, records)
        stati = dict(Counter(r['stato'] for r in records))
        print(f'Salvati {len(records)}/{len(prompts)} risultati in {finale}; stati: {stati}')
        if codice or len(records) != len(prompts):
            print('Generazione da controllare: nessun retry automatico. Conservare la cartella prima di riprendere.')
            raise SystemExit(1)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
