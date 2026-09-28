"""Prepara, controlla o genera un lotto OpenAI da un file di configurazione."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def comando(config, fase):
    richiesti = {'catalogo', 'totale', 'seed', 'prompts', 'output', 'deployment'}
    if set(config) != richiesti:
        raise ValueError('Campi richiesti: ' + ', '.join(sorted(richiesti)))
    if type(config['totale']) is not int or config['totale'] < 2 or config['totale'] % 2:
        raise ValueError('totale deve essere un intero positivo pari')
    if type(config['seed']) is not int:
        raise ValueError('seed deve essere un intero')
    for campo in richiesti - {'totale', 'seed'}:
        if not isinstance(config[campo], str) or not config[campo].strip():
            raise ValueError(f'{campo} deve essere una stringa non vuota')
    def percorso(campo):
        return str(ROOT / config[campo])
    if fase == 'prepara':
        return [sys.executable, str(ROOT / 'src/genera_prompt.py'),
                '--catalogo', percorso('catalogo'), '--totale', str(config['totale']),
                '--seed', str(config['seed']), '--output', percorso('prompts')]
    if fase not in {'controlla', 'genera'}:
        raise ValueError('Fase sconosciuta')
    # Verifica il lotto prima di qualsiasi chiamata: non basta il nome del file.
    records = [json.loads(line) for line in Path(percorso('prompts')).read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(records) != config['totale'] or any(r.get('seed') != config['seed'] for r in records):
        raise ValueError('Il file dei prompt non corrisponde a totale e seed della configurazione')
    cmd = [sys.executable, str(ROOT / 'src/genera_lotto.py'),
           '--input', percorso('prompts'), '--cartella-output', percorso('output'),
           '--deployment', config['deployment']]
    if fase == 'controlla':
        cmd.append('--solo-controllo')
    return cmd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fase', choices=['prepara', 'controlla', 'genera'])
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
