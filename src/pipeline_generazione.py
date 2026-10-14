"""Prepara, controlla o genera un corpus sintetico da un file di configurazione."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def comando(config, fase):
    richiesti = {'catalogo', 'totale', 'seed', 'prompts', 'output', 'deployment', 'versione_prompt'}
    opzionali = {'piano'}
    if not richiesti <= set(config) or set(config) - richiesti - opzionali:
        raise ValueError('Campi richiesti: ' + ', '.join(sorted(richiesti)))
    if type(config['totale']) is not int or config['totale'] < 2 or config['totale'] % 2:
        raise ValueError('totale deve essere un intero positivo pari')
    if type(config['seed']) is not int:
        raise ValueError('seed deve essere un intero')
    for campo in richiesti - {'totale', 'seed'}:
        if not isinstance(config[campo], str) or not config[campo].strip():
            raise ValueError(f'{campo} deve essere una stringa non vuota')
    if 'piano' in config and (not isinstance(config['piano'], str) or not config['piano'].strip()):
        raise ValueError('piano deve essere una stringa non vuota')
    def percorso(campo):
        return str(ROOT / config[campo])
    if fase == 'prepara':
        cmd = [sys.executable, str(ROOT / 'src/genera_prompt.py'),
               '--catalogo', percorso('catalogo'), '--seed', str(config['seed']),
               '--output', percorso('prompts')]
        if 'piano' in config:
            cmd.extend(['--piano', percorso('piano')])
        else:
            cmd.extend(['--totale', str(config['totale'])])
        return cmd
    if fase not in {'controlla', 'genera', 'riprendi'}:
        raise ValueError('Fase sconosciuta')
    # Verifica i prompt prima di qualsiasi chiamata: non basta il nome del file.
    records = [json.loads(line) for line in Path(percorso('prompts')).read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(records) != config['totale'] or any(r.get('seed') != config['seed'] for r in records):
        raise ValueError('Il file dei prompt non corrisponde a totale e seed della configurazione')
    if any(r.get('versione_prompt') != config['versione_prompt'] for r in records):
        raise ValueError('Il file dei prompt non corrisponde alla versione richiesta dalla configurazione')
    provenienze = [r.get('provenienza_locale', {}).get('sha256_file') for r in records]
    if any(not isinstance(p, dict) for p in provenienze) or any(p != provenienze[0] for p in provenienze[1:]):
        raise ValueError('Provenienza delle sorgenti assente o non uniforme nel file dei prompt')
    for nome, atteso in provenienze[0].items():
        candidati = [ROOT / cartella / nome for cartella in ('data', 'config')]
        presenti = [path for path in candidati if path.is_file()]
        if len(presenti) != 1:
            raise ValueError(f'Impossibile verificare univocamente la sorgente dei prompt: {nome}')
        corrente = hashlib.sha256(presenti[0].read_bytes()).hexdigest()
        if corrente != atteso:
            raise ValueError(f'Il file dei prompt è obsoleto rispetto alla sorgente corrente: {nome}')
    cmd = [sys.executable, str(ROOT / 'src/esegui_generazione.py'),
           '--input', percorso('prompts'), '--cartella-output', percorso('output'),
           '--deployment', config['deployment']]
    if fase == 'controlla':
        cmd.append('--solo-controllo')
    elif fase == 'riprendi':
        cmd.append('--riprendi')
    return cmd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fase', choices=['prepara', 'controlla', 'genera', 'riprendi'])
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding='utf-8'))
        if not isinstance(config, dict):
            raise ValueError('La configurazione deve essere un oggetto JSON')
        cmd = comando(config, args.fase)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    raise SystemExit(subprocess.run(cmd, cwd=ROOT, check=False).returncode)


if __name__ == '__main__':
    main()
