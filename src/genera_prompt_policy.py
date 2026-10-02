"""Genera prompt di policy separati dalle conversazioni e dal gold atteso."""

import argparse
import json
from pathlib import Path
import re

from esporta_dataset_masking import leggi

ROOT = Path(__file__).resolve().parents[1]


def istruzioni_policy(config):
    linee = "\n".join(f"- {x}" for x in config["indicazioni"])
    return f"""Valuta una conversazione sintetica e le detection già prodotte.
Per ogni detection restituisci una decisione contestuale. Non correggere gli
span e non aggiungere nuove detection.

Indicazioni della policy {config['versione']}:
{linee}

Restituisci soltanto JSON con il campo decisions: una lista con una voce per ogni
detection, composta da detection_id, action, replacement e reason.
Le action ammesse sono KEEP, MASK, GENERALIZE e REVIEW. replacement deve essere
null per KEEP e REVIEW. Per MASK deve essere un placeholder neutro formato
esclusivamente dal tipo della detection e da un numero, per esempio [PERSON_1]
o [ORGANIZATION_1]; non deve descrivere il ruolo nel caso. Per GENERALIZE deve
essere una formulazione meno specifica che conserva il ruolo utile, per esempio
«la società acquirente». Occorrenze dello stesso elemento devono ricevere lo
stesso replacement. La motivazione può essere discorsiva ma deve riferirsi al
contesto della conversazione. Non produrre una valutazione complessiva del rischio
residuo della conversazione: sarà oggetto di un esperimento separato. Questo è un
esperimento, non una certificazione di anonimizzazione."""


def valida_config(config):
    if (not isinstance(config, dict) or config.get("azioni") != ["KEEP", "MASK", "GENERALIZE", "REVIEW"]
            or not isinstance(config.get("versione"), str)
            or not isinstance(config.get("indicazioni"), list)):
        raise ValueError("Configurazione policy non valida")


def genera(records, config):
    valida_config(config)
    system = istruzioni_policy(config)
    for record in records:
        if record.get("stato") not in {"valido", "da_verificare"}:
            continue
        prompt = record.get("prompt", {})
        hypotheses = prompt.get("ipotesi_policy")
        detections = record.get("detection_attesa")
        conversation = record.get("chat", {}).get("conversazione")
        if not isinstance(hypotheses, list) or not isinstance(detections, list) or not conversation:
            raise ValueError("Record chat 5.0 privo di detection o ipotesi separate")
        by_reference = {h["reference_id"]: h for h in hypotheses}
        expected = []
        public_detections = []
        for detection in detections:
            reference_id = detection.get("metadata", {}).get("reference_id")
            if reference_id not in by_reference:
                raise ValueError("Detection senza ipotesi policy associata")
            hypothesis = by_reference[reference_id]
            expected.append({"detection_id": detection["detection_id"],
                             "expected_action": hypothesis["ipotesi_iniziale"],
                             "status": hypothesis["stato"]})
            public_detections.append({k: detection[k] for k in
                                      ("detection_id", "field", "start", "end", "text", "type")})
        policy_input = {"conversation": conversation, "detections": public_detections,
                        "policy_version": config["versione"]}
        yield {"id": record["id"], "versione_policy": config["versione"],
               "attese_policy": expected,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": json.dumps(policy_input, ensure_ascii=False, indent=2)}]}


def valida_risposta_policy(value, detections):
    if all(isinstance(d, str) for d in detections):
        detection_ids = list(detections)
        by_id = {}
    else:
        detection_ids = [d["detection_id"] for d in detections]
        by_id = {d["detection_id"]: d for d in detections}
    if not isinstance(value, dict) or set(value) != {"decisions"}:
        raise ValueError("Risposta policy non valida")
    decisions = value["decisions"]
    actions = {"KEEP", "MASK", "GENERALIZE", "REVIEW"}
    if (not isinstance(decisions, list) or len(decisions) != len(detection_ids)
            or {d.get("detection_id") for d in decisions} != set(detection_ids)):
        raise ValueError("Decisioni mancanti o duplicate")
    for decision in decisions:
        if (set(decision) != {"detection_id", "action", "replacement", "reason"}
                or decision["action"] not in actions
                or not isinstance(decision["reason"], str) or not decision["reason"].strip()
                or (decision["action"] in {"KEEP", "REVIEW"} and decision["replacement"] is not None)
                or (decision["action"] in {"MASK", "GENERALIZE"}
                    and (not isinstance(decision["replacement"], str) or not decision["replacement"].strip()))):
            raise ValueError("Decisione policy non valida")
        if decision["action"] == "MASK" and decision["detection_id"] in by_id:
            tipo = by_id[decision["detection_id"]]["type"]
            if not re.fullmatch(rf"\[{re.escape(tipo)}_[1-9][0-9]*\]", decision["replacement"]):
                raise ValueError("Placeholder MASK non neutro o incompatibile col tipo")
    if by_id:
        replacements = {}
        for decision in decisions:
            if decision["action"] not in {"MASK", "GENERALIZE"}:
                continue
            detection = by_id[decision["detection_id"]]
            key = (detection["text"], detection["type"], decision["action"])
            if key in replacements and replacements[key] != decision["replacement"]:
                raise ValueError("Replacement incoerente per occorrenze dello stesso elemento")
            replacements[key] = decision["replacement"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "config/policy_conversation_draft_2.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output già esistente")
        config = json.loads(args.config.read_text(encoding="utf-8"))
        rows = list(genera(leggi(args.input), config))
        if not rows:
            raise ValueError("Nessun record idoneo")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    print(f"Generati {len(rows)} prompt policy in {args.output}")


if __name__ == "__main__":
    main()
