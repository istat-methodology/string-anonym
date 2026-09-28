"""Una chiamata a Foundry per conversazione: Responses (GPT) o Messages (Claude)."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from validazione import valida, sostituisci, prepara_chat, prepara_testo

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://foundry-ateco.services.ai.azure.com/openai/v1/"
MODEL = "gpt-5.6-terra" # claude-sonnet-5

def scegli_provider(deployment, provider="auto"):
    if provider != "auto":
        return provider
    return "anthropic" if deployment.lower().startswith("claude-") else "openai"


def endpoint_provider(provider, esplicito=None):
    if esplicito:
        return esplicito.rstrip("/") + "/"
    if provider == "openai":
        return os.getenv("AZURE_OPENAI_ENDPOINT", ENDPOINT).rstrip("/") + "/"
    configurato = os.getenv("ANTHROPIC_FOUNDRY_BASE_URL")
    if configurato:
        return configurato.rstrip("/") + "/"
    # Stessa risorsa Foundry del pilota, percorso API distinto.
    base = urlsplit(os.getenv("AZURE_OPENAI_ENDPOINT", ENDPOINT))
    if not base.hostname or not base.hostname.endswith(".services.ai.azure.com"):
        raise ValueError("Specificare --endpoint con la base URL Anthropic della risorsa Foundry")
    return urlunsplit((base.scheme, base.netloc, "/anthropic/", "", ""))


def parametri_richiesta(prompt, deployment, max_tokens, provider):
    if provider == "openai":
        return dict(model=deployment, input=prompt["messages"],
                    text={"format": {"type": "json_object"}},
                    max_output_tokens=max_tokens, store=False)
    system = []
    messages = []
    for m in prompt["messages"]:
        if m["role"] == "system":
            system.append(m["content"])
        elif m["role"] in {"user", "assistant"}:
            messages.append(m)
        else:
            raise ValueError(f"Ruolo non supportato da Messages: {m['role']}")
    return dict(model=deployment, system="\n\n".join(system),
                messages=messages, max_tokens=max_tokens)


def estrai_testo(risposta, provider="openai"):
    """Legge la risposta originale senza correggere o ritagliare il JSON."""
    if provider == "anthropic":
        if risposta.get("stop_reason") != "end_turn":
            raise ValueError(f"Risposta Claude non completa: {risposta.get('stop_reason')}")
        blocchi = risposta.get("content", [])
        if any(c.get("type") not in {"text", "thinking", "redacted_thinking"} for c in blocchi):
            raise ValueError("Risposta Claude con contenuto non previsto")
        testo = "".join(c.get("text", "") for c in blocchi if c.get("type") == "text")
    elif provider == "openai":
        if risposta.get("status") != "completed":
            raise ValueError(f"Risposta non completa: {risposta.get('status')}")
        testo = "".join(c.get("text", "") for o in risposta.get("output", [])
                        for c in o.get("content", []) if c.get("type") == "output_text")
    else:
        raise ValueError(f"Provider non riconosciuto: {provider}")
    if not testo.strip():
        raise ValueError("Risposta senza testo")
    return testo


def main():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/chat_foundry.jsonl")
    parser.add_argument("--endpoint", help="Base URL del provider; per Claude termina in /anthropic")
    parser.add_argument("--provider", choices=("auto", "openai", "anthropic"), default="auto")
    parser.add_argument("--deployment", default=os.getenv("AZURE_OPENAI_DEPLOYMENT", MODEL))
    parser.add_argument("--max-conversazioni", "--limit", dest="limit", type=int, default=1, help="Numero di conversazioni (default: 1)")
    parser.add_argument("--id", help="Seleziona un singolo ID di prompt")
    parser.add_argument("--max-output-tokens", type=int, default=6000)
    args = parser.parse_args()
    if args.limit < 1 or args.max_output_tokens < 1:
        parser.error("Limiti non validi")
    provider = scegli_provider(args.deployment, args.provider)
    if provider == "anthropic":
        key = os.getenv("ANTHROPIC_FOUNDRY_API_KEY") or os.getenv("API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    else:
        key = os.getenv("API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    if not key:
        parser.error("Chiave mancante: impostare API_KEY nel .env")
    try:
        endpoint = endpoint_provider(provider, args.endpoint)
        if provider == "anthropic":
            from anthropic import AnthropicFoundry as Client, APIError
        else:
            from openai import OpenAI as Client, APIError
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
        print(f"Provider: {provider}; deployment: {args.deployment}", flush=True)
        with Client(base_url=endpoint, api_key=key,
                    timeout=120, max_retries=0) as client, args.output.open("x", encoding="utf-8") as f:
            for prompt in prompts:
                print(f"Generazione: {prompt['id']}", flush=True)
                parametri = parametri_richiesta(prompt, args.deployment, args.max_output_tokens, provider)
                record = {
                    "id": prompt["id"], "deployment": args.deployment,
                    "provider": provider, "endpoint": endpoint, "parametri_api": parametri,
                    "data_generazione": datetime.now(timezone.utc).isoformat(),
                    "max_output_tokens": args.max_output_tokens, "prompt": prompt,
                }
                try:
                    if provider == "anthropic":
                        response = client.messages.create(**parametri)
                    else:
                        response = client.responses.create(**parametri)
                    record["risposta_originale"] = response.model_dump(mode="json")
                    testo = estrai_testo(record["risposta_originale"], provider)
                    record.update(prepara_testo(testo, prompt["scheda"]))
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
    except ImportError:
        parser.error("Dipendenza mancante: installare requirements.txt nell’ambiente Python utilizzato")
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
