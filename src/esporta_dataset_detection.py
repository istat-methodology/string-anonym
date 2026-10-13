"""Esporta il corpus 5.0 per esperimenti di detection, senza policy negli input."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

from detection import DETECTION_TYPES, validate_detection
from esporta_dataset_masking import leggi

ROOT = Path(__file__).resolve().parents[1]
NER_TYPES = {"PERSON", "LOCATION"}


def leggi_comuni(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        if "Comune" not in (reader.fieldnames or []):
            raise ValueError("Colonna Comune mancante")
        comuni = {" ".join((row.get("Comune") or "").split()) for row in reader}
    comuni.discard("")
    if not comuni:
        raise ValueError("Catalogo comuni vuoto")
    return comuni


def _detection_component(parent, component, start, end, text):
    identity = json.dumps([parent["detection_id"], component, start, end], separators=(",", ":"))
    return {
        "detection_id": "det_" + hashlib.sha256(identity.encode()).hexdigest()[:16],
        "field": parent["field"], "start": start, "end": end, "text": text,
        "type": "LOCATION",
        "sources": [{"detector": "synthetic_address_component",
                     "component": component,
                     "parent_detection_id": parent["detection_id"]}],
    }


def espandi_address(detections, comuni):
    """Aggiunge strada+civico e comune come LOCATION annidate nell'ADDRESS."""
    if comuni is None:
        return list(detections), 0, 0
    result = list(detections)
    known = {(d["field"], d["start"], d["end"], d["type"]) for d in result}
    added = unresolved = 0
    for parent in list(detections):
        if parent["type"] != "ADDRESS":
            continue
        address = parent["text"]
        if "," not in address:
            unresolved += 1
            continue
        street_raw, city_raw = address.rsplit(",", 1)
        street, city = street_raw.strip(), city_raw.strip()
        if not street or city not in comuni:
            unresolved += 1
            continue
        street_local = address.index(street)
        city_local = address.rfind(city)
        for component, local_start, value in (
                ("street_civic", street_local, street),
                ("municipality", city_local, city)):
            start = parent["start"] + local_start
            end = start + len(value)
            detection = _detection_component(parent, component, start, end, value)
            key = (detection["field"], start, end, "LOCATION")
            if key not in known:
                result.append(detection); known.add(key); added += 1
    return result, added, unresolved


def _message_index(field):
    match = re.fullmatch(r"conversazione\.(\d+)\.testo", field)
    if not match:
        raise ValueError("La detection attesa deve riferirsi a un messaggio")
    return int(match[1])


def converti(record, identificativo, comuni=None):
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
        canoniche.append({
            "detection_id": detection_id,
            "field": detection["field"],
            "start": start,
            "end": end,
            "text": detection["text"],
            "type": detection["type"],
            "sources": [dict(source) for source in detection["sources"]],
        })

    canoniche, _, _ = espandi_address(canoniche, comuni)
    canoniche.sort(key=lambda d: (d["field"], d["start"], d["end"], d["type"]))
    # Vista transitoria: esclude le componenti annidate aggiunte dal nuovo gold.
    legacy = [d for d in canoniche
              if not any(s.get("detector") == "synthetic_address_component"
                         for s in d["sources"])]
    adattatore = [{
        "campo": d["field"], "start": d["start"], "end": d["end"],
        "tipo": d["type"], "testo": d["text"],
    } for d in legacy]
    return ({"id": identificativo, "conversazione": conversazione},
            {"id": identificativo, "detections": canoniche},
            {"id": identificativo, "annotazioni": adattatore})


def esporta(fonti, destinazione, comuni=None):
    if destinazione.exists():
        raise ValueError("La cartella di destinazione deve essere nuova")
    inputs, gold, adapters, ner_gold, provenance, excluded = [], [], [], [], [], []
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
                inp, expected, adapter = converti(record, identifier, comuni)
            except (ValueError, KeyError, TypeError, IndexError) as error:
                excluded.append({**trace, "motivo": str(error)})
                continue
            inputs.append(inp)
            gold.append(expected)
            adapters.append(adapter)
            ner_gold.append({"id": identifier, "annotazioni": [
                {"campo": d["field"], "start": d["start"], "end": d["end"],
                 "tipo": d["type"], "testo": d["text"]}
                for d in expected["detections"] if d["type"] in NER_TYPES]})
            provenance.append(trace)
            categories.update(d["type"] for d in expected["detections"])
            roles.update(inp["conversazione"][_message_index(d["field"])]["sender"]
                         for d in expected["detections"])
            negatives += not expected["detections"]

    if not inputs:
        raise ValueError("Nessun record esportabile")
    manifest = {
        "versione": "detection-5.1-multilivello" if comuni is not None else "detection-5.0",
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
        "gold_ner": "annotazioni_ner_attese.jsonl contiene PERSON e LOCATION, incluse le componenti LOCATION degli ADDRESS.",
        "regola_address": ("ADDRESS completo; strada+civico e comune come LOCATION annidate, solo con comune verificato."
                            if comuni is not None else "Nessuna espansione multilivello."),
    }
    destinazione.mkdir(parents=True, exist_ok=False)
    for name, rows in (
        ("input.jsonl", inputs),
        ("detections_attese.jsonl", gold),
        ("annotazioni_attese.jsonl", adapters),
        ("annotazioni_ner_attese.jsonl", ner_gold),
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
    parser.add_argument("--comuni", type=Path,
                        help="Catalogo codici_comuni.csv: abilita il gold ADDRESS multilivello")
    args = parser.parse_args()
    try:
        comuni = leggi_comuni(args.comuni) if args.comuni else None
        result = esporta(args.input, args.output, comuni)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps({k: result[k] for k in (
        "record_letti", "esportati", "esclusi", "detection_attese",
        "conversazioni_negative", "categorie", "detection_per_ruolo")}, ensure_ascii=False))
    print(f"Salvato in: {args.output}")


if __name__ == "__main__":
    main()
