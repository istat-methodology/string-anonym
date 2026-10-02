"""Formato comune e merge dei risultati prodotti dai detector."""

import hashlib
import json


# Elenco operativo dei tipi supportati, non classificazione generale del dominio.
DETECTION_TYPES = {
    'PERSON', 'ORGANIZATION', 'LOCATION', 'ADDRESS', 'EMAIL', 'PHONE',
    'COD_UTENTE', 'PASSWORD', 'NUM_PRATICA', 'CODICE_FISCALE',
    'PARTITA_IVA', 'COD_INDAGINE', 'INDAGINE', 'DATE', 'ROLE', 'OFFICE',
}


def _source_key(source):
    return json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def validate_detection(detection, fields):
    """Valida una detection rispetto ai testi originali, senza applicare policy."""
    required = {'field', 'start', 'end', 'text', 'type', 'sources'}
    if not isinstance(detection, dict) or not required <= detection.keys():
        raise ValueError('Detection incompleta')
    field = detection['field']
    if field not in fields or not isinstance(fields[field], str):
        raise ValueError('Campo della detection non disponibile')
    start, end = detection['start'], detection['end']
    text = fields[field]
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(text)
            or text[start:end] != detection['text']):
        raise ValueError('Offset o testo della detection non validi')
    if detection['type'] not in DETECTION_TYPES:
        raise ValueError('Tipo di detection non supportato')
    sources = detection['sources']
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(s, dict) or not isinstance(s.get('detector'), str)
                   or not s['detector'] for s in sources)):
        raise ValueError('Sorgente della detection non valida')


def merge_detection(detections, fields, record_id=None):
    """Unisce solo detection identiche; conflitti e sovrapposizioni restano visibili.

    Due risultati descrivono la stessa detection soltanto quando campo, offset e
    tipo coincidono. Gli span sovrapposti o con tipo diverso non vengono eliminati:
    sono informazione utile per le fasi successive.
    """
    merged = {}
    for detection in detections:
        validate_detection(detection, fields)
        key = (detection['field'], detection['start'], detection['end'], detection['type'])
        if key not in merged:
            merged[key] = {k: detection[k] for k in ('field', 'start', 'end', 'text', 'type')}
            merged[key]['sources'] = []
            merged[key]['metadata'] = dict(detection.get('metadata', {}))
        target = merged[key]
        known = {_source_key(source) for source in target['sources']}
        for source in detection['sources']:
            if _source_key(source) not in known:
                target['sources'].append(dict(source))
                known.add(_source_key(source))

    result = []
    for key in sorted(merged, key=lambda x: (x[0], x[1], x[2], x[3])):
        detection = merged[key]
        identity = json.dumps([record_id, *key], ensure_ascii=False, separators=(',', ':'))
        detection['detection_id'] = 'det_' + hashlib.sha256(identity.encode()).hexdigest()[:16]
        result.append(detection)
    return result
