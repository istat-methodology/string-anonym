"""Una chiamata Responses a Foundry per ciascun prompt JSONL selezionato."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from validazione import valida, sostituisci, prepara_chat

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://foundry-ateco.services.ai.azure.com/openai/v1/"


def main():
    from dotenv import load_dotenv
    from openai import OpenAI, APIError

    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/chat_foundry.jsonl")
    parser.add_argument("--endpoint", default=os.getenv("AZURE_OPENAI_ENDPOINT", ENDPOINT))
    parser.add_argument("--deployment", default=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.6-terra"))
    parser.add_argument("--max-conversazioni", "--limit", dest="limit", type=int, default=1, help="Numero di conversazioni (default: 1)")
    parser.add_argument("--id", help="Seleziona un singolo ID di prompt")
    parser.add_argument("--max-output-tokens", type=int, default=6000)
    args = parser.parse_args()
    if args.limit < 1 or args.max_output_tokens < 1:
        parser.error("Limiti non validi")
    key = os.getenv("API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    if not key:
        parser.error("Chiave mancante: impostare API_KEY nel .env")
    try:
        if args.output.exists():
            raise ValueError("Output già esistente: scegliere un nuovo percorso")
        prompts = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
        if args.id:
            prompts = [p for p in prompts if p["id"] == args.id]
        prompts = prompts[:args.limit]
        if not prompts:
            raise ValueError("Nessun prompt selezionato")
        for p in prompts:
            for e in p["scheda"]["entita_previste"]:
                if not e.get("valore_proposto"):
                    raise ValueError("Usare i prompt aggiornati con valore_proposto")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        errori = 0
        with OpenAI(base_url=args.endpoint.rstrip("/") + "/", api_key=key,
                    timeout=120, max_retries=0) as client, args.output.open("x", encoding="utf-8") as f:
            for prompt in prompts:
                print(f"Generazione: {prompt['id']}", flush=True)
                record = {
                    "id": prompt["id"], "deployment": args.deployment,
                    "data_generazione": datetime.now(timezone.utc).isoformat(),
                    "max_output_tokens": args.max_output_tokens, "prompt": prompt,
                }
                try:
                    response = client.responses.create(
                        model=args.deployment, input=prompt["messages"],
                        text={"format": {"type": "json_object"}},
                        max_output_tokens=args.max_output_tokens, store=False,
                    )
                    record["risposta_originale"] = response.model_dump(mode="json")
                    if response.status != "completed":
                        raise ValueError(f"Risposta non completa: {response.status}")
                    chat = json.loads(response.output_text)
                    record.update(prepara_chat(chat, prompt["scheda"]))
                    if record["stato"] != "valido":
                        errori += 1
                except APIError as error:
                    # Non stampare corpi degli errori o header di autenticazione.
                    record.update(stato="errore_api", errore=type(error).__name__,
                                  http_status=getattr(error, "status_code", None))
                    errori += 1
                except (ValueError, KeyError, TypeError) as error:
                    record.update(stato="da_verificare", errore=str(error))
                    errori += 1
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                print(f"  {record['stato']}", flush=True)
                if record["stato"] == "errore_api":
                    break
        print(f"Output: {args.output}")
        if errori:
            raise SystemExit(1)
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
