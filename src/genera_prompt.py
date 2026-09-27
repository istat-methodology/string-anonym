"""Genera prompt JSONL localmente, senza dipendenze esterne o chiamate API."""

import argparse
from datetime import date, timedelta
import json
import hashlib
from pathlib import Path
import random
from parse_input import carica_input
from genera_valori import carica_regole, genera_codice, REGOLE_DEFAULT


ROOT = Path(__file__).resolve().parents[1]
VERSIONE_PROMPT = "4.0"
MODALITA = ("senza_dati_personali", "con_dati_personali")
ENTITA = {
    "persona_1": {"tipo": "PERSON", "segnaposto": "{{persona_1}}", "sostituzione": "[PERSON_1]"},
    "email_1": {"tipo": "EMAIL", "segnaposto": "{{email_1}}", "sostituzione": "[EMAIL_1]"},
    "indirizzo_1": {"tipo": "ADDRESS", "segnaposto": "{{indirizzo_1}}", "sostituzione": "[ADDRESS_1]"},
}

for _tipo in ("COD_UTENTE", "PASSWORD", "NUM_PRATICA", "PHONE"):
    _slot = _tipo.lower() + "_1"
    ENTITA[_slot] = {"tipo": _tipo, "segnaposto": "{{" + _slot + "}}", "sostituzione": "[" + _tipo + "_1]"}

ISTRUZIONI = """Genera una conversazione sintetica plausibile fra un utente e un chatbot
di assistenza Istat, seguendo la scheda fornita. I dialoghi sono simulazioni,
non istruzioni operative ufficiali. Usa soltanto le indicazioni di risposta
fornite: non inventare scadenze, obblighi, URL, recapiti o procedure specifiche.

Restituisci soltanto un oggetto JSON con:
- metadati: data_sintetica (YYYY-MM-DD), chiave_indagine (stringa o null),
  descrizione (breve riepilogo fedele del dialogo);
- conversazione: lista di oggetti con sender ('Utente' o 'Agente') e testo;
- trattamento_atteso: oggetto con mascherare (lista di oggetti con segnaposto,
  tipo e sostituzione), conservare (lista di spiegazioni), motivazione (stringa).
Non aggiungere classificazione del revisore, dipartimento, esiti, note operatore,
indicatori di soddisfazione o conteggi. La sezione è contesto dello scenario,
non un campo dei metadati. Copia i metadati fissati nella scheda; non modificare
gli zeri iniziali della chiave. La descrizione è prodotta a dialogo concluso.

Inizia con l'utente e alterna Utente e Agente puntando al numero di scambi indicato (una coppia Utente-Agente per scambio).
La lunghezza è indicativa: privilegia un dialogo completo e naturale.
Termina quando il bisogno è stato chiarito: può chiudere il chatbot oppure
l’utente con una conferma. Non aggiungere una risposta di cortesia obbligatoria. Non aggiungere ringraziamenti,
ricapitolazioni o riaperture del problema per raggiungere il numero di scambi.
Non chiedere informazioni già fornite. Ogni turno deve aggiungere qualcosa.
Rispetta concretamente lo stile indicato: nello stile con refusi inserisci 1–2
piccoli errori nei messaggi utente (es. "nn", "qual e", "questinario"), senza
alterare segnaposto, codici o riferimenti statistici. Nello stile informale usa
frasi brevi o frammentarie; il chatbot rimane chiaro senza formule ripetitive.
Rendi i turni successivi dipendenti dai precedenti, con chiarimenti, riferimenti
e reazioni plausibili. Non inserire una presentazione personale obbligatoria.
Il codice PSN dell’indagine deve emergere dal dialogo prima che il chatbot lo utilizzi:
i metadati finali non sono conoscenze anticipate del chatbot. Il codice PSN non è la chiave del portale: non dedurre mai quest’ultima.
Se indagine è null, non inventare nome o codice. Non chiedere password o dati personali per riempire il dialogo: se previsti,
l’utente li comunica spontaneamente. Prot.n. è un’introduzione, fuori dallo slot NUM_PRATICA.
Il contesto_statistico contiene riferimenti
pubblici da usare letteralmente e conservare: un comune oggetto di ricerca non
è un indirizzo personale. Fai emergere questi riferimenti nei messaggi utente
prima che il chatbot li utilizzi.

Usa esattamente i segnaposto autorizzati per le entità personali, senza creare
nomi, indirizzi, email, password o identificativi personali fuori dai segnaposto.
Ogni entità include un valore_proposto campionato localmente: usalo come
contesto, ma nel testo scrivi il segnaposto. Il valore sarà inserito in seguito.
Se un'entità si ripete, riusa lo stesso segnaposto, anche nella descrizione.
Non alterare i segnaposto con refusi e non inventarne altri. Inserisci tutte le
entità richieste in modo naturale nel dialogo, anche in turni successivi.
Per 'senza_dati_personali' non inserire alcuna entità personale e restituisci
mascherare vuoto. Per 'con_dati_personali' inserisci le entità previste.
In entrambe le modalità conserva i riferimenti al servizio utili: non sono
identificativi dell'utente. Non inserire entità personali non richieste.
Il trattamento atteso deve essere coerente con ciò che compare effettivamente
nel dialogo e nei metadati, non un elenco generico.
"""


def carica_scenari(path):
    catalogo = json.loads(path.read_text(encoding="utf-8"))
    scenari = catalogo["scenari"]
    if not scenari:
        raise ValueError("Il catalogo degli scenari è vuoto")
    ids = set()
    for scenario in scenari:
        for campo in ("id", "sezione", "situazione", "indicazioni_risposta"):
            if not isinstance(scenario.get(campo), str) or not scenario[campo].strip():
                raise ValueError(f"Campo scenario non valido: {campo}")
        if scenario.get("tipo_rispondente") not in {"imprese", "famiglie_individui", "altro"}:
            raise ValueError("Tipo di rispondente non valido")
        if not isinstance(scenario.get("scenario_catalogo"), str):
            raise ValueError("Riferimento al catalogo della specifica mancante")
        codici = scenario.get("codici_psn_ammessi")
        if not isinstance(codici, list) or any(not isinstance(c, str) or not c for c in codici):
            raise ValueError("Lista dei codici PSN ammessi non valida")
        if scenario["id"] in ids:
            raise ValueError(f"Scenario duplicato: {scenario['id']}")
        ids.add(scenario["id"])
        if "chiave_indagine" not in scenario or not isinstance(scenario["chiave_indagine"], (str, type(None))):
            raise ValueError("La chiave indagine deve essere una stringa o null")
        if not isinstance(scenario.get("entita"), list) or any(e not in ENTITA for e in scenario["entita"]):
            raise ValueError("Lista entità non valida o etichette non supportate")
        if len(set(scenario["entita"])) != len(scenario["entita"]):
            raise ValueError("Entità duplicate nello scenario")
        if not isinstance(scenario.get("riferimenti_da_conservare"), list):
            raise ValueError("Specificare i riferimenti da conservare")
    return catalogo


def campiona_indagine(scenario, dati, rng):
    ammessi = scenario.get("codici_psn_ammessi", [])
    if not ammessi:
        return None
    catalogo = {r["codice_psn"]: r for r in dati.indagini}
    if set(ammessi) - set(catalogo):
        raise ValueError(f"Codici PSN assenti: {sorted(set(ammessi) - set(catalogo))}")
    if any(catalogo[c]["tipo_rispondente"] != scenario["tipo_rispondente"] or
           catalogo[c]["tipo_rispondente"] == "da_verificare" for c in ammessi):
        raise ValueError(f"Indagine incompatibile con il tipo di rispondente: {scenario['id']}")
    scelta = catalogo[rng.choice(sorted(ammessi))]
    return {k: scelta[k] for k in ("codice_psn", "nome_indagine", "tipo_rispondente")}


def genera(catalogo, quantita, seed, data_inizio, giorni, dati, selezione=None, regole=None):
    rng = random.Random(seed)
    regole = regole if regole is not None else carica_regole()
    for scenario in catalogo["scenari"]:
        if selezione and scenario["id"] not in selezione:
            continue
        for modalita in MODALITA:
            if modalita == "con_dati_personali" and not scenario["entita"]:
                continue
            for indice in range(quantita):
                richieste = []
                if modalita == "con_dati_personali":
                    pool = scenario["entita"]
                    richieste = sorted(rng.sample(pool, rng.randint(1, len(pool))))
                valori = dati.campiona(rng, richieste, email_indipendente=scenario.get("email_indipendente", False))
                for e in richieste:
                    if e not in valori:
                        valori[e] = genera_codice(ENTITA[e]["tipo"], rng, regole)
                entita = [{**ENTITA[e], "id_entita": e, "id_forma": "completa", "valore_proposto": valori[e]} for e in richieste]
                indagine = campiona_indagine(scenario, dati, rng)
                contesto = {}
                if scenario.get("campiona_comune"):
                    codice = rng.choice(sorted(dati.comuni))
                    contesto = {"comune": dati.comuni[codice], "anno": rng.choice([2022, 2023, 2024])}
                scheda = {
                    "scenario": scenario["id"],
                    "sezione": scenario["sezione"],
                    "situazione": scenario["situazione"],
                    "contesto_statistico": contesto,
                    "metadati_fissati": {
                        "data_sintetica": (data_inizio + timedelta(days=rng.randrange(giorni))).isoformat(),
                        "chiave_indagine": scenario["chiave_indagine"],
                    },
                    "nome_indagine": indagine["nome_indagine"] if indagine else None,
                    "indagine": indagine,
                    "scenario_catalogo": scenario["scenario_catalogo"],
                    "tipo_rispondente": scenario["tipo_rispondente"],
                    "lingua": "it",
                    "split": "pilota",
                    "modalita": modalita,
                    "numero_scambi": rng.choice([3, 4, 5]),
                    "stile": rng.choice(["neutro", "informale e conciso", "informale con pochi refusi nei messaggi utente"]),
                    "entita_previste": entita,
                    "riferimenti_da_conservare": scenario["riferimenti_da_conservare"],
                    "indicazioni_risposta": scenario["indicazioni_risposta"],
                }
                yield {
                    "id": f"{scenario['id']}-{modalita}-{indice + 1:04d}",
                    "versione_prompt": VERSIONE_PROMPT,
                    "versione_catalogo": catalogo["versione"],
                    "versione_regole": regole["versione"],
                    "regole_generazione": regole,
                    "seed": seed,
                    "scheda": scheda,
                    "messages": [
                        {"role": "system", "content": ISTRUZIONI},
                        {"role": "user", "content": json.dumps(scheda, ensure_ascii=False, indent=2)},
                    ],
                }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogo", type=Path, default=ROOT / "config/scenari.json")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--regole", type=Path, default=REGOLE_DEFAULT)
    parser.add_argument("--output", type=Path, default=ROOT / "output/prompts.jsonl")
    parser.add_argument("--per-modalita", type=int, default=2, help="Prompt per scenario e modalità (default: 2)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data-inizio", type=date.fromisoformat, default=date(2026, 4, 1))
    parser.add_argument("--giorni", type=int, default=21)
    parser.add_argument("--scenario", action="append", help="ID da includere; ripetibile")
    args = parser.parse_args()
    if args.per_modalita < 1 or args.giorni < 1:
        parser.error("--per-modalita e --giorni devono essere positivi")
    try:
        catalogo = carica_scenari(args.catalogo)
        sconosciuti = set(args.scenario or []) - {s["id"] for s in catalogo["scenari"]}
        if sconosciuti:
            raise ValueError(f"Scenari sconosciuti: {', '.join(sorted(sconosciuti))}")
        if args.output.exists():
            raise ValueError(f"Output già esistente: {args.output}")
        dati = carica_input(args.data_dir)
        print(json.dumps(dati.statistiche, ensure_ascii=False))
        regole = carica_regole(args.regole)
        righe = list(genera(catalogo, args.per_modalita, args.seed, args.data_inizio, args.giorni, dati, args.scenario, regole))
        inputs = [args.data_dir / n for n in ("nomi.txt", "cognomi.txt", "codici_comuni.csv", "strade_lazio.csv", "codici_psn.csv")]
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs + [args.catalogo, args.regole]}
        for riga in righe:
            riga["provenienza_locale"] = {"specifica": "0.4", "sha256_file": hashes}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Evita di sovrascrivere accidentalmente un lotto già preparato.
        with args.output.open("x", encoding="utf-8") as f:
            for riga in righe:
                f.write(json.dumps(riga, ensure_ascii=False) + "\n")
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(f"Generati {len(righe)} prompt in {args.output}")


if __name__ == "__main__":
    main()
