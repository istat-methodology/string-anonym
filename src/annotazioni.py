"""Offset Unicode Python, start incluso ed end escluso, per singolo campo."""

import re

SLOT = re.compile(r'\{\{[^{}]+\}\}')


def sostituisci_con_span(testo, entita, campo):
    mappa = {e['segnaposto']: e for e in entita}
    if len(mappa) != len(entita):
        raise ValueError('Segnaposto duplicati')
    parti, spans = [], []
    cursor = offset = 0
    for match in SLOT.finditer(testo):
        if match[0] not in mappa:
            raise ValueError(f'Segnaposto non previsto: {match[0]}')
        e = mappa[match[0]]
        valore = e['valore_proposto']
        if not isinstance(valore, str) or not valore or '{{' in valore or '}}' in valore:
            raise ValueError('Valore dello slot vuoto o contenente segnaposto')
        prefisso = testo[cursor:match.start()]
        parti.extend((prefisso, valore))
        offset += len(prefisso)
        spans.append({'campo': campo, 'start': offset, 'end': offset + len(valore),
                      'tipo': e['tipo'], 'id_entita': e['id_entita'],
                      'id_forma': e.get('id_forma', 'completa'), 'testo': valore,
                      'sostituzione': e['sostituzione']})
        offset += len(valore)
        cursor = match.end()
    parti.append(testo[cursor:])
    finale = ''.join(parti)
    if '{{' in finale or '}}' in finale:
        raise ValueError('Delimitatori di segnaposto residui o malformati')
    valida_span(finale, spans)
    return finale, spans


def valida_span(testo, spans):
    fine = 0
    for span in spans:
        start, end = span['start'], span['end']
        if (type(start) is not int or type(end) is not int or
                not fine <= start < end <= len(testo) or testo[start:end] != span['testo']):
            raise ValueError('Span non valido o sovrapposto')
        fine = end
