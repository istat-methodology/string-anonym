"""Esporta il corpus 5.0 per esperimenti di detection, senza policy negli input."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from detection import DETECTION_TYPES, validate_detection
from esporta_dataset_masking import leggi


def _message_index(field):
    match = re.fullmatch(r"conversazione\.(\d+)\.testo", field)
    if not match:
        raise ValueError("La detection attesa deve riferirsi a un messaggio")
    return int(match[1])


def converti(record, identificativo):
    """Separa input, gold canonico e adattatore legacy senza mutare il record."""
    if record.get("stato") != "valido":
        raise ValueError("Validazione della chat non superata")
    messaggi = record["chat"]["conversazione"]
    if not isinstance(messaggi, list) or not messaggi:
        raise ValueError("Conversazione vuota o non valida")
    conversazione = []
    fields = {}
    for indice, messaggio in enumerate(messaggi):
        if (not isinstance(messaggio, dict)
                or set(messaggio) != {"sender", "testo"}
                or messaggio["sender"] not in {"Utente", "Agente"}
                or not isinstance(messaggio["testo"], str)
                or not messaggio["testo"].strip()):
            raise ValueError("Messaggio non valido")
        conversazione.append({"sender": messaggio["sender"], "testo": messaggio["testo"]})
        fields[f"conversazione.{indice}.testo"] = messaggio["testo"]

    detections = record.get("detection_attesa")
    if not isinstance(detections, list):
        raise ValueError("detection_attesa deve essere una lista")
    canoniche = []
    ids = set()
    intervalli = {}
    for detection in detections:
        validate_detection(detection, fields)
        detection_id = detection.get("detection_id")
        if not isinstance(detection_id, str) or not detection_id or detection_id in ids:
            raise ValueError("detection_id assente o duplicato")
        ids.add(detection_id)
        indice = _message_index(detection["field"])
        if indice >= len(conversazione):
            raise ValueError("Indice del messaggio fuori intervallo")
        start, end = detection["start"], detection["end"]
        for altro_start, altro_end in intervalli.get(indice, []):
            if start < altro_end and end > altro_start:
                raise ValueError("Detection attese sovrapposte: adattatore non rappresentabile")
        intervalli.setdefault(indice, []).append((start, end))
        canoniche.append({
            "detection_id": detection_id,
            "field": detection["field"],
            "start": start,
            "end": end,
            "text": detection["text"],
            "type": detection["type"],
            "sources": [dict(source) for source in detection["sources"]],
        })

    canoniche.sort(key=lambda d: (d["field"], d["start"], d["end"], d["type"]))
    adattatore = [{
        "campo": d["field"], "start": d["start"], "end": d["end"],
        "tipo": d["type"], "testo": d["text"],
    } for d in canoniche]
    return ({"id": identificativo, "conversazione": conversazione},
            {"id": identificativo, "detections": canoniche},
            {"id": identificativo, "annotazioni": adattatore})


def esporta(fonti, destinazione):
    if destinazione.exists():
        raise ValueError("La cartella di destinazione deve essere nuova")
    inputs, gold, adapters, provenance, excluded = [], [], [], [], []
    source_hashes = set()
    record_ids = set()
    source_manifest = []
    categories = Counter()
    roles = Counter()
    negatives = 0
    for path in fonti:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in source_hashes:
            raise ValueError("Fonte duplicata")
        source_hashes.add(digest)
        source_manifest.append({"path": str(path.resolve()), "sha256": digest})
        for number, record in enumerate(leggi(path), 1):
            original_id = record.get("id")
            identifier = f"{digest}:{original_id}"
            trace = {"id": identifier, "id_originale": original_id,
                     "fonte_sha256": digest, "record": number,
                     "stato_validazione": record.get("stato")}
            if identifier in record_ids:
                raise ValueError("ID duplicato nella fonte")
            record_ids.add(identifier)
            try:
                inp, expected, adapter = converti(record, identifier)
            except (ValueError, KeyError, TypeError, IndexError) as error:
                excluded.append({**trace, "motivo": str(error)})
                continue
            inputs.append(inp)
            gold.append(expected)
            adapters.append(adapter)
            provenance.append(trace)
            categories.update(d["type"] for d in expected["detections"])
            roles.update(inp["conversazione"][_message_index(d["field"])]["sender"]
                         for d in expected["detections"])
            negatives += not expected["detections"]

    if not inputs:
        raise ValueError("Nessun record esportabile")
    manifest = {
        "versione": "detection-5.0",
        "uso": "sviluppo sintetico; non test finale indipendente né gold revisionato umano",
        "step": "1-detection-messaggio",
        "fonti": source_manifest,
        "record_letti": len(record_ids),
        "esportati": len(inputs),
        "esclusi": len(excluded),
        "conversazioni_negative": negatives,
        "detection_attese": sum(categories.values()),
        "categorie": dict(sorted(categories.items())),
        "detection_per_ruolo": dict(sorted(roles.items())),
        "input_modello": "Solo conversazione con testi e ruoli; nessuna policy, scheda o annotazione attesa.",
        "gold": "Offset sintetici da slot e riferimenti controllati; da revisionare prima di una valutazione finale.",
        "adattatore": "annotazioni_attese.jsonl mantiene il formato del runner legacy; detections_attese.jsonl è canonico.",
    }
    destinazione.mkdir(parents=True, exist_ok=False)
    for name, rows in (
        ("input.jsonl", inputs),
        ("detections_attese.jsonl", gold),
        ("annotazioni_attese.jsonl", adapters),
        ("provenienza.jsonl", provenance),
        ("esclusi.jsonl", excluded),
    ):
        with (destinazione / name).open("x", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
    (destinazione / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = esporta(args.input, args.output)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps({k: result[k] for k in (
        "record_letti", "esportati", "esclusi", "detection_attese",
        "conversazioni_negative", "categorie", "detection_per_ruolo")}, ensure_ascii=False))
    print(f"Salvato in: {args.output}")


if __name__ == "__main__":
    main()
