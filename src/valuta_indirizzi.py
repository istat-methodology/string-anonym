"""Valuta la protezione degli indirizzi dopo il benchmark NER standard."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from esporta_dataset_masking import leggi
from valuta_masking import indicizza


CIVIC_RE = re.compile(
    r"(?i)(\d+[a-z]?(?:[/-][a-z0-9]+)?(?:\s*(?:bis|ter|quater))?)\s*$"
)


def posizioni_significative(start, text):
    """Posizioni alfanumeriche: spazi e punteggiatura non diventano leakage."""
    return {start + i for i, char in enumerate(text) if char.isalnum()}


def componente(parent, children, name):
    matches = [child for child in children if any(
        source.get("detector") == "synthetic_address_component"
        and source.get("parent_detection_id") == parent["detection_id"]
        and source.get("component") == name
        for source in child.get("sources", [])
    )]
    if len(matches) != 1:
        raise ValueError(f"Componente {name} assente o duplicata per {parent['detection_id']}")
    return matches[0]


def estrai_indirizzi(record):
    detections = record.get("detections")
    if not isinstance(detections, list):
        raise ValueError("Gold canonico privo di detections")
    addresses = []
    for parent in (d for d in detections if d.get("type") == "ADDRESS"):
        metadata_components = parent.get("metadata", {}).get("address_components")
        if metadata_components:
            def combine(*names):
                parts = [metadata_components[name] for name in names if name in metadata_components]
                if not parts:
                    return None
                start = min(part["start"] for part in parts)
                end = max(part["end"] for part in parts)
                local_start, local_end = start - parent["start"], end - parent["start"]
                return {"start": start, "end": end,
                        "text": parent["text"][local_start:local_end]}
            components = {
                "street": combine("street_type", "street_name"),
                "house_number": combine("house_number", "house_extension"),
                "internal": combine("internal"),
                "municipality": combine("municipality"),
            }
            components = {name: value for name, value in components.items() if value}
            if "street" not in components:
                raise ValueError("ADDRESS senza componente strada")
            addresses.append({
                "address_id": parent["detection_id"], "field": parent["field"],
                "full": {"start": parent["start"], "end": parent["end"], "text": parent["text"]},
                "components": components,
            })
            continue
        street_civic = componente(parent, detections, "street_civic")
        municipality = componente(parent, detections, "municipality")
        match = CIVIC_RE.search(street_civic["text"])
        if not match:
            raise ValueError(f"Civico non riconoscibile in {street_civic['text']!r}")
        civic_start = street_civic["start"] + match.start(1)
        street_text = street_civic["text"][:match.start(1)].rstrip(" ,")
        if not street_text:
            raise ValueError("Componente strada vuota")
        addresses.append({
            "address_id": parent["detection_id"],
            "field": parent["field"],
            "full": {"start": parent["start"], "end": parent["end"], "text": parent["text"]},
            "components": {
                "street": {"start": street_civic["start"],
                           "end": street_civic["start"] + len(street_text), "text": street_text},
                "house_number": {"start": civic_start,
                                 "end": civic_start + len(match.group(1)), "text": match.group(1)},
                "municipality": {"start": municipality["start"], "end": municipality["end"],
                                 "text": municipality["text"]},
            },
        })
    return addresses


def posizioni_predette(record, field):
    positions = set()
    for annotation in record.get("annotazioni", []):
        if annotation.get("campo") != field or annotation.get("tipo") != "LOCATION":
            continue
        start, end = annotation.get("start"), annotation.get("end")
        if type(start) is not int or type(end) is not int or start >= end:
            raise ValueError("Span predetto non valido")
        positions.update(range(start, end))
    return positions


def classifica(components, full_complete):
    if full_complete:
        return "complete"
    street = components["street"]["complete"]
    civic = components.get("house_number", {}).get("complete")
    municipality = components.get("municipality", {}).get("complete")
    any_covered = any(value["covered_characters"] for value in components.values())
    others = [value["complete"] for name, value in components.items()
              if name != "house_number"]
    if "house_number" in components and not civic and all(others):
        return "house_number_exposed"
    others = [value["complete"] for name, value in components.items()
              if name != "municipality"]
    if "municipality" in components and not municipality and all(others):
        return "municipality_exposed"
    if (municipality and not street
            and not any(value["covered_characters"] for name, value in components.items()
                        if name != "municipality")):
        return "municipality_only"
    if not any_covered:
        return "uncovered"
    return "partial_other"


def valuta(inputs, gold, predictions):
    inputs, gold, predictions = map(indicizza, (inputs, gold, predictions))
    if not inputs or inputs.keys() != gold.keys():
        raise ValueError("Input e gold devono avere gli stessi ID")
    if predictions.keys() - inputs.keys():
        raise ValueError("Predizioni estranee al dataset")

    totals = Counter()
    component_totals = {name: Counter() for name in
                        ("street", "house_number", "internal", "municipality")}
    outcomes = Counter()
    details = []
    failures = []
    for identifier, inp in inputs.items():
        addresses = estrai_indirizzi(gold[identifier])
        prediction = predictions.get(identifier)
        if prediction is None or prediction.get("stato") == "errore":
            if addresses:
                failures.append({"id": identifier, "addresses": len(addresses),
                                 "reason": "missing" if prediction is None else prediction.get("errore")})
            continue
        if prediction.get("stato") != "ok":
            raise ValueError("Stato della predizione non valido")
        for address in addresses:
            field = address["field"]
            match = re.fullmatch(r"conversazione\.(\d+)\.testo", field)
            if not match:
                raise ValueError("Campo ADDRESS non valido")
            text = inp["conversazione"][int(match.group(1))]["testo"]
            predicted = posizioni_predette(prediction, field)
            component_results = {}
            for name, item in address["components"].items():
                expected = posizioni_significative(item["start"], item["text"])
                covered = expected & predicted
                result = {
                    "expected_characters": len(expected),
                    "covered_characters": len(covered),
                    "coverage": len(covered) / len(expected) if expected else None,
                    "complete": bool(expected) and expected <= predicted,
                }
                component_results[name] = result
                component_totals[name]["expected"] += len(expected)
                component_totals[name]["covered"] += len(covered)
                component_totals[name]["complete"] += result["complete"]
                component_totals[name]["total"] += 1

            expected = posizioni_significative(address["full"]["start"], address["full"]["text"])
            covered = expected & predicted
            residual = sorted(expected - predicted)
            outcome = classifica(component_results, not residual)
            outcomes[outcome] += 1
            totals["addresses"] += 1
            totals["expected"] += len(expected)
            totals["covered"] += len(covered)
            totals["complete"] += not residual
            details.append({
                "id": identifier,
                "address_id": address["address_id"],
                "field": field,
                "text": address["full"]["text"],
                "coverage": len(covered) / len(expected) if expected else None,
                "complete": not residual,
                "outcome": outcome,
                "components": component_results,
                "residual_text": "".join(text[position] for position in residual),
            })

    if not totals["addresses"]:
        raise ValueError("Nessun indirizzo valutabile")
    components = {}
    for name, count in component_totals.items():
        components[name] = {
            "complete": count["complete"],
            "total": count["total"],
            "complete_rate": count["complete"] / count["total"] if count["total"] else None,
            "character_coverage": count["covered"] / count["expected"] if count["expected"] else None,
        }
    return {
        "version": "address-eval-1.0",
        "scope": "Post-hoc complement to exact-match PERSON/LOCATION metrics; predictions unchanged.",
        "addresses_evaluated": totals["addresses"],
        "technical_failures": failures,
        "full_address": {
            "complete": totals["complete"],
            "total": totals["addresses"],
            "complete_rate": totals["complete"] / totals["addresses"],
            "character_coverage": totals["covered"] / totals["expected"],
            "residual_exposure_rate": 1 - totals["covered"] / totals["expected"],
        },
        "components": components,
        "outcomes": dict(sorted(outcomes.items())),
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output già esistente")
        result = valuta(leggi(args.input), leggi(args.gold), leggi(args.predictions))
        result["sources"] = {
            name: {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in (("input", args.input), ("gold", args.gold),
                               ("predictions", args.predictions))
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        parser.error(str(error))
    print(json.dumps({"addresses_evaluated": result["addresses_evaluated"],
                      "full_address": result["full_address"],
                      "outcomes": result["outcomes"]}, ensure_ascii=False))
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
