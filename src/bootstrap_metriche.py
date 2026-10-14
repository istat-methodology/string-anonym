"""Bootstrap appaiato per conversazione sulle predizioni NER congelate."""

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics

from esporta_dataset_masking import leggi
from valuta_indirizzi import estrai_indirizzi, posizioni_predette, posizioni_significative
from valuta_masking import indicizza, metriche, span_validi


ROOT = Path(__file__).resolve().parents[1]
TIPI = ("PERSON", "LOCATION")
METRICHE_CONFRONTO = (
    "micro.f1", "PERSON.f1", "LOCATION.f1",
    "address.complete_rate", "address.character_coverage",
)


def percentile(values, probability):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def riassumi(values, estimate, confidence):
    values = [value for value in values if value is not None]
    if not values:
        raise ValueError("Distribuzione bootstrap vuota")
    alpha = (1 - confidence) / 2
    mean = statistics.fmean(values)
    variance = statistics.variance(values) if len(values) > 1 else 0.0
    return {
        "estimate": estimate,
        "bootstrap_mean": mean,
        "bias": mean - estimate,
        "variance": variance,
        "standard_error": math.sqrt(variance),
        "ci_lower": percentile(values, alpha),
        "ci_upper": percentile(values, 1 - alpha),
        "confidence": confidence,
        "replicates_valid": len(values),
    }


def conteggi_per_conversazione(inputs, expected, predictions):
    inputs, expected, predictions = map(indicizza, (inputs, expected, predictions))
    if inputs.keys() != expected.keys() or inputs.keys() != predictions.keys():
        raise ValueError("Input, gold e predizioni devono avere gli stessi ID")
    result = {}
    for identifier, record in inputs.items():
        prediction = predictions[identifier]
        if prediction.get("stato") != "ok":
            raise ValueError(f"Predizione non valida per bootstrap appaiato: {identifier}")
        conversation = record["conversazione"]
        gold = span_validi(expected[identifier]["annotazioni"], conversation, set(TIPI))
        predicted = span_validi(prediction["annotazioni"], conversation, set(TIPI))
        counts = {"micro": Counter(), **{name: Counter() for name in TIPI}}
        for label, spans in (("tp", gold & predicted),
                             ("fp", predicted - gold),
                             ("fn", gold - predicted)):
            counts["micro"][label] = len(spans)
            for *_, entity_type in spans:
                counts[entity_type][label] += 1
        result[identifier] = counts
    return result


def indirizzi_per_conversazione(inputs, gold, predictions):
    inputs, gold, predictions = map(indicizza, (inputs, gold, predictions))
    if inputs.keys() != gold.keys() or inputs.keys() != predictions.keys():
        raise ValueError("Input, gold indirizzi e predizioni devono avere gli stessi ID")
    result = {}
    for identifier, record in inputs.items():
        prediction = predictions[identifier]
        if prediction.get("stato") != "ok":
            raise ValueError(f"Predizione non valida per bootstrap appaiato: {identifier}")
        counts = Counter()
        for address in estrai_indirizzi(gold[identifier]):
            expected = posizioni_significative(address["full"]["start"],
                                                address["full"]["text"])
            predicted = posizioni_predette(prediction, address["field"])
            counts["total"] += 1
            counts["complete"] += expected <= predicted
            counts["characters_expected"] += len(expected)
            counts["characters_covered"] += len(expected & predicted)
        result[identifier] = counts
    return result


def calcola_metriche(ids, ner_units, address_units):
    output = {}
    for scope in ("micro", *TIPI):
        counts = Counter()
        for identifier in ids:
            counts.update(ner_units[identifier][scope])
        output[scope] = metriche(counts["tp"], counts["fp"], counts["fn"])
    address = Counter()
    for identifier in ids:
        address.update(address_units[identifier])
    output["address"] = {
        "complete": address["complete"],
        "total": address["total"],
        "complete_rate": (address["complete"] / address["total"]
                          if address["total"] else None),
        "characters_expected": address["characters_expected"],
        "characters_covered": address["characters_covered"],
        "character_coverage": (address["characters_covered"] / address["characters_expected"]
                               if address["characters_expected"] else None),
    }
    return output


def valore(metrics, path):
    section, name = path.split(".", 1)
    return metrics[section][name]


def bootstrap(inputs, expected, gold_addresses, predictions_by_model,
              replicates=10000, seed=20261014, confidence=0.95):
    if type(replicates) is not int or replicates < 2:
        raise ValueError("repliche deve essere un intero almeno pari a 2")
    if not 0 < confidence < 1:
        raise ValueError("confidence deve essere fra 0 e 1")
    ids = [record["id"] for record in inputs]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Dataset vuoto o con ID duplicati")

    units = {}
    point = {}
    distributions = {}
    for model, predictions in predictions_by_model.items():
        ner = conteggi_per_conversazione(inputs, expected, predictions)
        address = indirizzi_per_conversazione(inputs, gold_addresses, predictions)
        units[model] = (ner, address)
        point[model] = calcola_metriche(ids, ner, address)
        distributions[model] = {path: [] for path in METRICHE_CONFRONTO}
        for scope in ("micro", *TIPI):
            for name in ("precision", "recall", "f1"):
                distributions[model].setdefault(f"{scope}.{name}", [])

    generator = random.Random(seed)
    for _ in range(replicates):
        sample = generator.choices(ids, k=len(ids))
        for model, (ner, address) in units.items():
            metrics = calcola_metriche(sample, ner, address)
            for path in distributions[model]:
                distributions[model][path].append(valore(metrics, path))

    model_reports = {}
    for model in predictions_by_model:
        summaries = {}
        for path, values in distributions[model].items():
            summaries[path] = riassumi(values, valore(point[model], path), confidence)
        model_reports[model] = {"point": point[model], "bootstrap": summaries}

    comparisons = []
    for first, second in itertools.combinations(predictions_by_model, 2):
        for path in METRICHE_CONFRONTO:
            values = [a - b for a, b in zip(distributions[first][path],
                                             distributions[second][path])
                      if a is not None and b is not None]
            estimate = valore(point[first], path) - valore(point[second], path)
            summary = riassumi(values, estimate, confidence)
            summary.update({"first": first, "second": second, "metric": path})
            comparisons.append(summary)

    return {
        "version": "paired-conversation-bootstrap-1.0",
        "unit": "conversation",
        "paired": True,
        "replicates": replicates,
        "seed": seed,
        "confidence": confidence,
        "interval": "percentile",
        "conversations": len(ids),
        "models": model_reports,
        "paired_differences": comparisons,
        "interpretation_limit": (
            "Intervals quantify sampling variability conditional on the synthetic corpus "
            "and generation design; they do not establish generalization to real traffic."
        ),
    }


def markdown(report):
    lines = [
        "# Bootstrap appaiato per conversazione — run 3", "",
        f"Repliche: {report['replicates']}; seed: {report['seed']}; "
        f"IC: {report['confidence']:.0%} percentile; conversazioni: {report['conversations']}.", "",
        "| Modello | F1 micro (IC) | F1 PERSON (IC) | F1 LOCATION (IC) | Indirizzi completi (IC) | Copertura caratteri (IC) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    def cell(summary):
        return (f"{summary['estimate']:.3f} "
                f"[{summary['ci_lower']:.3f}, {summary['ci_upper']:.3f}]")
    for model, data in report["models"].items():
        boot = data["bootstrap"]
        lines.append("| " + " | ".join((model, cell(boot["micro.f1"]),
            cell(boot["PERSON.f1"]), cell(boot["LOCATION.f1"]),
            cell(boot["address.complete_rate"]),
            cell(boot["address.character_coverage"]))) + " |")
    lines.extend(["", "Gli intervalli descrivono la variabilità di campionamento condizionata al corpus sintetico e al suo disegno di generazione; non misurano la generalizzazione al traffico reale.", ""])
    return "\n".join(lines)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        config_path = args.config if args.config.is_absolute() else ROOT / args.config
        config = json.loads(config_path.read_text(encoding="utf-8"))
        paths = {key: ROOT / config[key] for key in
                 ("input", "attese", "gold_indirizzi", "run_dir", "output", "markdown_output")}
        if paths["output"].exists() or paths["markdown_output"].exists():
            raise ValueError("Output bootstrap già esistente")
        inputs = leggi(paths["input"])
        expected = leggi(paths["attese"])
        gold_addresses = leggi(paths["gold_indirizzi"])
        predictions = {}
        prediction_paths = {}
        for model in config["models"]:
            path = paths["run_dir"] / model / "predizioni.jsonl"
            predictions[model] = leggi(path)
            prediction_paths[model] = path
        result = bootstrap(inputs, expected, gold_addresses, predictions,
                           config.get("replicates", 10000), config.get("seed", 20261014),
                           config.get("confidence", 0.95))
        source_paths = {"config": config_path, "input": paths["input"],
                        "attese": paths["attese"], "gold_indirizzi": paths["gold_indirizzi"],
                        **{f"predictions_{model}": path
                           for model, path in prediction_paths.items()}}
        result["sources"] = {name: {"path": str(path.resolve()), "sha256": sha256(path)}
                             for name, path in source_paths.items()}
        paths["output"].parent.mkdir(parents=True, exist_ok=True)
        paths["output"].write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
        paths["markdown_output"].write_text(markdown(result), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(f"Bootstrap completato: {result['replicates']} repliche appaiate")
    print(f"JSON: {paths['output']}")
    print(f"Markdown: {paths['markdown_output']}")


if __name__ == "__main__":
    main()
