"""Esegue i prompt di policy su Foundry e valida localmente le decisioni."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from genera_chat import (MODEL, endpoint_provider, estrai_testo,
                         parametri_richiesta, scegli_provider)
from genera_prompt_policy import valida_risposta_policy


ROOT = Path(__file__).resolve().parents[1]


def prepara_risposta_policy(testo, prompt):
    """Accetta JSON puro o una sola cornice Markdown e valida il contratto."""
    testo = testo.strip()
    cornice = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", testo, re.DOTALL)
    contenuto = cornice.group(1) if cornice else testo
    value = json.loads(contenuto)
    policy_input = json.loads(prompt["messages"][1]["content"])
    valida_risposta_policy(value, policy_input["detections"])
    return value, (["Rimossa unica cornice Markdown dal JSON della risposta"]
                   if cornice else [])


def main():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", help="Base URL del provider")
    parser.add_argument("--provider", choices=("auto", "openai", "anthropic"), default="auto")
    parser.add_argument("--deployment", default=os.getenv("AZURE_OPENAI_DEPLOYMENT", MODEL))
    parser.add_argument("--max-prompt", "--limit", dest="limit", type=int, default=1)
    parser.add_argument("--id", help="Seleziona un singolo ID")
    parser.add_argument("--max-output-tokens", type=int, default=4000)
    args = parser.parse_args()
    if args.limit < 1 or args.max_output_tokens < 1:
        parser.error("Limiti non validi")
    provider = scegli_provider(args.deployment, args.provider)
    key = ((os.getenv("ANTHROPIC_FOUNDRY_API_KEY") if provider == "anthropic" else None)
           or os.getenv("API_KEY") or os.getenv("AZURE_OPENAI_API_KEY"))
    if not key:
        parser.error("Chiave Foundry mancante nel file .env")
    try:
        endpoint = endpoint_provider(provider, args.endpoint)
        if provider == "anthropic":
            from anthropic import AnthropicFoundry as Client, APIError
        else:
            from openai import OpenAI as Client, APIError
        if args.output.exists():
            raise ValueError("Output già esistente: scegliere un nuovo percorso")
        prompts = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        if args.id:
            prompts = [p for p in prompts if p["id"] == args.id]
        prompts = prompts[:args.limit]
        if not prompts:
            raise ValueError("Nessun prompt selezionato")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        errori = 0
        print(f"Provider: {provider}; deployment: {args.deployment}", flush=True)
        with Client(base_url=endpoint, api_key=key, timeout=120, max_retries=0) as client, \
                args.output.open("x", encoding="utf-8") as file:
            for prompt in prompts:
                print(f"Policy: {prompt['id']}", flush=True)
                params = parametri_richiesta(prompt, args.deployment,
                                             args.max_output_tokens, provider)
                record = {
                    "id": prompt["id"], "versione_policy": prompt["versione_policy"],
                    "deployment": args.deployment, "provider": provider,
                    "endpoint": endpoint, "data_generazione": datetime.now(timezone.utc).isoformat(),
                    "prompt": prompt,
                }
                try:
                    response = (client.messages.create(**params) if provider == "anthropic"
                                else client.responses.create(**params))
                    record["risposta_originale"] = response.model_dump(mode="json")
                    text = estrai_testo(record["risposta_originale"], provider)
                    value, correzioni = prepara_risposta_policy(text, prompt)
                    record.update(stato="valido", policy=value,
                                  validazione={"correzioni": correzioni})
                except APIError as error:
                    record.update(stato="errore_api", errore=type(error).__name__,
                                  http_status=getattr(error, "status_code", None))
                    errori += 1
                except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
                    record.update(stato="da_verificare", errore=str(error))
                    errori += 1
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
                file.flush()
                print(f"  {record['stato']}", flush=True)
                if record["stato"] == "errore_api":
                    break
        print(f"Output: {args.output}")
        if errori:
            raise SystemExit(1)
    except ImportError:
        parser.error("Dipendenza mancante: installare requirements.txt")
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
