"""Recupera risposte salvate senza effettuare chiamate API."""

import argparse
from collections import Counter
import copy
import json
from pathlib import Path

from validazione import prepara_chat


def rivalida(record):
    nuovo = copy.deepcopy(record)
    nuovo["verifica_precedente"] = {k: record[k] for k in ("stato", "errore", "validazione") if k in record}
    for campo in ("errore", "chat", "chat_template", "validazione"):
        nuovo.pop(campo, None)
    try:
        risposta = record.get("risposta_originale", {})
        if risposta.get("status") != "completed":
            raise ValueError("Risposta originale assente o incompleta")
        testo = "".join(c.get("text", "") for o in risposta.get("output", [])
                        for c in o.get("content", []) if c.get("type") == "output_text")
        nuovo.update(prepara_chat(json.loads(testo), record["prompt"]["scheda"]))
    except (ValueError, KeyError, TypeError) as error:
        nuovo.update(stato="da_verificare", errore=str(error))
    return nuovo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    conteggi = Counter()
    try:
        records = [json.loads(l) for l in args.input.read_text(encoding="utf-8").splitlines() if l.strip()]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as f:
            for record in records:
                nuovo = rivalida(record)
                f.write(json.dumps(nuovo, ensure_ascii=False) + "\n")
                conteggi[nuovo["stato"]] += 1
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(dict(conteggi), ensure_ascii=False))
    print(f"Salvato: {args.output}")


if __name__ == "__main__":
    main()
