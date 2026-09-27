"""Generatori semplici; formati e parametri modificabili nel JSON delle regole."""

import json
from pathlib import Path

REGOLE_DEFAULT = Path(__file__).resolve().parents[1] / 'config/regole_generazione.json'


def carica_regole(path=REGOLE_DEFAULT):
    regole = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(regole.get('versione'), str):
        raise ValueError('Versione delle regole mancante')
    for variante in regole['COD_UTENTE']['varianti']:
        _cifre_valide(variante['cifre'])
        if not isinstance(variante['prefisso'], str):
            raise ValueError('Prefisso codice utente non valido')
    if not regole['COD_UTENTE']['varianti']:
        raise ValueError('Nessuna variante di codice utente')
    _cifre_valide(regole['NUM_PRATICA']['cifre'])
    pratica = regole['NUM_PRATICA']
    if not pratica['anni'] or any(not isinstance(a, str) or len(a) != 2 or not a.isascii() or not a.isdigit() for a in pratica['anni']):
        raise ValueError('Gli anni della pratica devono essere stringhe di due cifre')
    if not isinstance(pratica['separatore'], str) or not pratica['separatore']:
        raise ValueError('Separatore pratica non valido')
    password = regole['PASSWORD']
    if not password['lunghezze'] or not isinstance(password['alfabeto'], str) or not password['alfabeto']:
        raise ValueError('Regola password vuota')
    for lunghezza in password['lunghezze']:
        _cifre_valide(lunghezza)
    phone = regole['PHONE']
    _cifre_valide(phone['cifre'])
    if not isinstance(phone['inizio'], str) or not phone['inizio'].isdigit():
        raise ValueError('Inizio telefono non valido')
    for campo in ('separatori', 'prefissi'):
        if not phone[campo] or any(not isinstance(v, str) for v in phone[campo]):
            raise ValueError(f'Regola telefono non valida: {campo}')
    return regole


def _cifre_valide(n):
    if type(n) is not int or not 1 <= n <= 64:
        raise ValueError('Lunghezza richiesta fra 1 e 64')


def cifre(rng, n):
    return ''.join(rng.choice('0123456789') for _ in range(n))


def genera_codice(tipo, rng, regole):
    if tipo not in regole or regole[tipo].get('stato') == 'in_attesa_di_formato':
        raise ValueError(f'Formato non disponibile per {tipo}')
    r = regole[tipo]
    if tipo == 'COD_UTENTE':
        variante = rng.choice(r['varianti'])
        return variante['prefisso'] + cifre(rng, variante['cifre'])
    if tipo == 'NUM_PRATICA':
        return cifre(rng, r['cifre']) + r['separatore'] + rng.choice(r['anni'])
    if tipo == 'PASSWORD':
        return ''.join(rng.choice(r['alfabeto']) for _ in range(rng.choice(r['lunghezze'])))
    if tipo == 'PHONE':
        numero = r['inizio'] + cifre(rng, r['cifre'])
        sep = rng.choice(r['separatori'])
        return rng.choice(r['prefissi']) + sep.join((numero[:3], numero[3:6], numero[6:]))
    raise ValueError(f'Generatore non disponibile per {tipo}')
