"""Genera prompt JSONL localmente, senza dipendenze esterne o chiamate API."""

import argparse
from datetime import date, timedelta
import json
import hashlib
from pathlib import Path
import random
import re
from parse_input import ADDRESS_VARIANTS, carica_input
from genera_valori import carica_regole, genera_codice, REGOLE_DEFAULT


ROOT = Path(__file__).resolve().parents[1]
VERSIONE_PROMPT = "5.1-address"
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
Non sollecitare valori personali nemmeno con formule facoltative come «se vuole,
può indicare il recapito» o domande sulle credenziali utilizzate. Quando previsti,
questi valori compaiono per iniziativa dell'utente. Puoi chiedere invece cosa
succede, quale dubbio rimane o quale dettaglio statistico serve.
Evita spiegazioni sulle categorie di dati quando non risolvono un dubbio emerso.
Segui lo sviluppo specifico della situazione: non imporre a ogni dialogo una
presentazione completa, una distinzione fra codici e un riepilogo conclusivo.
La natura sintetica dei dati è un'informazione per il generatore, non un fatto
della conversazione: non chiamare i valori «fittizi» o «sintetici» nei messaggi
o nella descrizione. Non menzionare detection, masking, policy o anonimizzazione.
In assenza di indicazioni esplicite, suggerisci di sottoporre il problema
all'assistenza perché valuti la richiesta. Non anticipare verifiche d'identità,
documenti necessari, aggiornamenti dell'account o esiti del recupero.
Se l'utente chiede conferma di una procedura non documentata, non confermarla:
chiarisci che i passaggi e la possibilità di risolvere il problema vanno verificati
con l'assistenza. Non basta usare il condizionale per introdurre una procedura
non fornita. I vincoli di generazione guidano il comportamento del chatbot:
non trasformarli in frasi come «senza che questo comporti una modifica dell'account».

Restituisci soltanto un oggetto JSON con:
- metadati: data_sintetica (YYYY-MM-DD), chiave_indagine (stringa o null),
  descrizione (breve riepilogo fedele del dialogo);
- conversazione: lista di oggetti con sender ('Utente' o 'Agente') e testo.
Non aggiungere annotazioni, trattamento atteso, decisioni o valutazioni. Questi
elementi saranno costruiti in fasi separate senza essere affidati al generatore.
Fai comparire naturalmente nel dialogo tutti i riferimenti_detection elencati
nella scheda. Non trasformarli in un elenco artificiale.
Non aggiungere classificazione del revisore, dipartimento, esiti, note operatore,
indicatori di soddisfazione o conteggi. La sezione è contesto dello scenario,
non un campo dei metadati. Copia i metadati fissati nella scheda; non modificare
gli zeri iniziali della chiave. La descrizione è prodotta a dialogo concluso.
Riassumi solo quanto emerge dai messaggi: distingui i fatti dichiarati dall'utente
dalle ipotesi del chatbot e non attenuare nel riepilogo eventuali promesse o certezze
espresse nel dialogo.

Inizia con l'utente, alterna sempre Utente e Agente e termina con l'Agente.
Una coppia Utente-Agente è uno scambio. Genera almeno 3 scambi completi, quindi
almeno 6 messaggi non vuoti, e usa numero_scambi come obiettivo. Distribuisci
le informazioni dello scenario fra turni diversi: richiesta iniziale, almeno un
chiarimento o nuovo dettaglio pertinente e risposta conclusiva. Ogni passaggio
deve far avanzare il dialogo; non usare cortesia, ripetizioni o riepiloghi come
riempitivo. Puoi fermarti prima di numero_scambi soltanto dopo almeno 3 scambi,
quando continuare richiederebbe di inventare informazioni o procedure.
Termina quando il bisogno è stato chiarito, con una risposta sostanziale
dell'Agente all'ultimo messaggio dell'utente. Non aggiungere una risposta di
sola cortesia, ringraziamenti, ricapitolazioni o riaperture del problema per
raggiungere il numero di scambi. Ogni messaggio deve avere testo non vuoto.
Non chiedere informazioni già fornite, neppure come conferma, salvo una reale
contraddizione o ambiguità nei messaggi. Se l'utente ha già dichiarato il ruolo,
non domandare nuovamente se sia responsabile o delegato.
Se l'utente accetta il passo successivo, l'Agente chiude con una breve indicazione
pertinente, non con un ringraziamento o un riepilogo. Ogni turno deve aggiungere qualcosa.
Rispetta concretamente lo stile indicato: nello stile con refusi inserisci 1–2
piccoli errori nei messaggi utente (es. "nn", "qual e", "questinario"), senza
alterare segnaposto, codici o riferimenti statistici. Nello stile informale usa
frasi brevi o frammentarie; il chatbot rimane chiaro senza formule ripetitive.
Nello stile neutro usa italiano standard, senza refusi intenzionali o abbreviazioni
come «nn». Inserisci refusi soltanto quando lo stile li richiede esplicitamente.
I refusi richiesti sono 1–2 nell'intera conversazione, soltanto nei messaggi
dell'utente. Il chatbot usa sempre italiano corretto, anche nelle citazioni:
può ripetere gli slot, ma non copiare gli errori ortografici dell'utente.
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
Il segnaposto ADDRESS rappresenta l'intera forma superficiale assegnata: non
anteporre o aggiungere parole come via, piazza, civico, interno o comune. Alcune
forme sono intenzionalmente incomplete e devono restare tali.
Ogni entità include un valore_proposto campionato localmente: usalo come
contesto, ma nel testo scrivi il segnaposto. Il valore sarà inserito in seguito.
Se un'entità si ripete, riusa lo stesso segnaposto, anche nella descrizione.
Non alterare i segnaposto con refusi e non inventarne altri. Inserisci tutte le
entità richieste in modo naturale nel dialogo, anche in turni successivi.
Per 'senza_dati_personali' non inserire alcuna entità personale. Per
'con_dati_personali' inserisci le entità previste.
Quando uno slot non è previsto, menziona soltanto il concetto senza inventare
valori: «la pratica precedente», non un numero dopo «Prot. n.». Questa regola
vale anche nelle risposte del chatbot, nelle citazioni e nei riepiloghi.
In entrambe le modalità conserva i riferimenti al servizio utili: non sono
identificativi dell'utente. Non inserire entità personali non richieste.
Se è presente copertura_mirata, fai comparire gli slot in ripetere_agente
prima nei messaggi utente e poi almeno una volta in un messaggio del chatbot.
La ripetizione serve a una citazione o a un chiarimento pertinente: non implica
registrazione, invio o presa in carico. Non chiedere identificativi per ottenerla.
Sono casi sintetici di prova del masking, anche per le credenziali fittizie.
I riferimenti_letterali devono comparire nel dialogo in chiaro, fuori dagli slot,
nel significato pubblico indicato dalla scheda; non sono identità da mascherare.
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
        if scenario.get("campionamento_entita", "sottoinsieme") not in {"sottoinsieme", "tutte"}:
            raise ValueError("Campionamento entità non valido")
        ripetere = scenario.get("ripetere_agente", [])
        if (not isinstance(ripetere, list) or any(e not in scenario["entita"] for e in ripetere)
                or len(set(ripetere)) != len(ripetere)):
            raise ValueError("Ripetizioni richieste non compatibili con le entità")
        if ripetere and scenario.get("campionamento_entita") != "tutte":
            raise ValueError("Le ripetizioni mirate richiedono campionamento_entita=tutte")
        if not isinstance(scenario.get("riferimenti_da_conservare"), list):
            raise ValueError("Specificare i riferimenti da conservare")
        statici = scenario.get("riferimenti_statici", [])
        if (not isinstance(statici, list)
                or any(not isinstance(r, dict)
                       or set(r) != {"id", "riferimento", "tipo", "ipotesi_iniziale", "stato"}
                       or r["ipotesi_iniziale"] not in {"KEEP", "MASK", "GENERALIZE", "REVIEW"}
                       or r["stato"] not in {"APPROVED", "PROVISIONAL", "OPEN"}
                       for r in statici)):
            raise ValueError("Riferimenti statici non validi")
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


def genera(catalogo, quantita, seed, data_inizio, giorni, dati, selezione=None,
           regole=None, totale=None, modalita_selezionate=None,
           entita_obbligatorie=None, varianti_indirizzo=None, id_lotto=None):
    rng = random.Random(seed)
    regole = regole if regole is not None else carica_regole()
    scenari = [s for s in catalogo["scenari"] if not selezione or s["id"] in selezione]
    if totale is not None:
        if totale < 2 or totale % 2 or not scenari or any(not s["entita"] for s in scenari):
            raise ValueError("--totale richiede un numero positivo pari e scenari con entrambe le modalità")
        base, resto = divmod(totale // 2, len(scenari))
    modalita_selezionate = tuple(modalita_selezionate or MODALITA)
    if not set(modalita_selezionate) <= set(MODALITA) or not modalita_selezionate:
        raise ValueError("Modalità selezionate non valide")
    entita_obbligatorie = set(entita_obbligatorie or [])
    if entita_obbligatorie - set(ENTITA):
        raise ValueError("Entità obbligatorie non valide")
    varianti_indirizzo = tuple(varianti_indirizzo or ())
    if set(varianti_indirizzo) - set(ADDRESS_VARIANTS):
        raise ValueError("Varianti indirizzo non valide")
    if varianti_indirizzo and ("indirizzo_1" not in entita_obbligatorie
                               or modalita_selezionate != ("con_dati_personali",)):
        raise ValueError("Le varianti indirizzo richiedono ADDRESS obbligatorio e sola modalità con dati")
    for posizione, scenario in enumerate(scenari):
        quantita_scenario = quantita if totale is None else base + (posizione < resto)
        for modalita in modalita_selezionate:
            if modalita == "con_dati_personali" and not scenario["entita"]:
                continue
            for indice in range(quantita_scenario):
                richieste = []
                if modalita == "con_dati_personali":
                    pool = scenario["entita"]
                    richieste = (sorted(pool) if scenario.get("campionamento_entita") == "tutte"
                                 else sorted(rng.sample(pool, rng.randint(1, len(pool)))))
                    if entita_obbligatorie - set(pool):
                        raise ValueError(f"Entità obbligatorie assenti dallo scenario: {scenario['id']}")
                    richieste = sorted(set(richieste) | entita_obbligatorie)
                address_variant = (varianti_indirizzo[indice % len(varianti_indirizzo)]
                                   if varianti_indirizzo else None)
                valori = dati.campiona(
                    rng, richieste,
                    email_indipendente=scenario.get("email_indipendente", False),
                    address_variant=address_variant,
                )
                for e in richieste:
                    if e not in valori:
                        valori[e] = genera_codice(ENTITA[e]["tipo"], rng, regole)
                entita = []
                for e in richieste:
                    entity = {**ENTITA[e], "id_entita": e, "id_forma": "completa",
                              "valore_proposto": valori[e]}
                    if e == "indirizzo_1":
                        entity.update(valori["indirizzo_1__metadata"])
                    entita.append(entity)
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
                    "lingua": scenario.get("lingua", "it"),
                    "split": "pilota",
                    "modalita": modalita,
                    "numero_scambi": rng.choice([3, 4, 5]),
                    "stile": rng.choice(["neutro", "informale e conciso", "informale con pochi refusi nei messaggi utente"]),
                    "entita_previste": entita,
                    "riferimenti_da_conservare": scenario["riferimenti_da_conservare"],
                    "indicazioni_risposta": scenario["indicazioni_risposta"],
                }
                if scenario.get("campionamento_entita") == "tutte":
                    riferimenti = [indagine["codice_psn"]] if indagine else []
                    if contesto:
                        riferimenti.extend([contesto["comune"], str(contesto["anno"])])
                    scheda["copertura_mirata"] = {
                        "ripetere_agente": [ENTITA[e]["segnaposto"] for e in scenario.get("ripetere_agente", []) if e in richieste],
                        "riferimenti_letterali": riferimenti,
                    }
                riferimenti_analisi = [{
                    "reference_id": e["id_entita"],
                    "riferimento": e["segnaposto"],
                    "tipo": e["tipo"],
                    "ipotesi_iniziale": "MASK",
                    "stato": "APPROVED",
                } for e in entita]
                if indagine:
                    riferimenti_analisi.extend([
                        {"reference_id": "codice_indagine", "riferimento": indagine["codice_psn"],
                         "tipo": "COD_INDAGINE", "ipotesi_iniziale": "KEEP", "stato": "APPROVED"},
                        {"reference_id": "nome_indagine", "riferimento": indagine["nome_indagine"],
                         "tipo": "INDAGINE", "ipotesi_iniziale": "KEEP", "stato": "APPROVED"},
                    ])
                if contesto:
                    riferimenti_analisi.extend([
                        {"reference_id": "comune_ricerca", "riferimento": contesto["comune"],
                         "tipo": "LOCATION", "ipotesi_iniziale": "KEEP", "stato": "APPROVED"},
                        {"reference_id": "periodo_ricerca", "riferimento": str(contesto["anno"]),
                         "tipo": "DATE", "ipotesi_iniziale": "KEEP", "stato": "APPROVED"},
                    ])
                riferimenti_analisi.extend({
                    "reference_id": r["id"], "riferimento": r["riferimento"],
                    "tipo": r["tipo"], "ipotesi_iniziale": r["ipotesi_iniziale"],
                    "stato": r["stato"],
                } for r in scenario.get("riferimenti_statici", []))
                scheda["schema_output"] = "chat_v5"
                scheda["riferimenti_detection"] = [
                    {k: r[k] for k in ("reference_id", "riferimento", "tipo")}
                    for r in riferimenti_analisi]
                record = {
                    "id": "-".join(filter(None, (
                        id_lotto, scenario["id"], modalita, f"{indice + 1:04d}"))),
                    "versione_prompt": VERSIONE_PROMPT,
                    "versione_catalogo": catalogo["versione"],
                    "versione_regole": regole["versione"],
                    "regole_generazione": regole,
                    "seed": seed,
                    "scheda": scheda,
                    "ipotesi_policy": riferimenti_analisi,
                    "messages": [
                        {"role": "system", "content": ISTRUZIONI},
                        {"role": "user", "content": json.dumps(scheda, ensure_ascii=False, indent=2)},
                    ],
                }
                yield record


def genera_da_piano(catalogo, piano, seed, data_inizio, giorni, dati, regole):
    """Espande batch espliciti mantenendo quote e provenienza nel prompt."""
    if (not isinstance(piano, dict) or set(piano) != {"versione", "totale", "batch"}
            or not isinstance(piano["versione"], str)
            or type(piano["totale"]) is not int or piano["totale"] < 1
            or not isinstance(piano["batch"], list) or not piano["batch"]):
        raise ValueError("Piano di generazione non valido")
    scenario_ids = {scenario["id"] for scenario in catalogo["scenari"]}
    records = []
    batch_ids = set()
    required = {"id", "per_scenario_modalita", "scenari", "modalita"}
    optional = {"entita_obbligatorie", "varianti_indirizzo"}
    for index, batch in enumerate(piano["batch"]):
        if not isinstance(batch, dict) or set(batch) - required - optional or not required <= set(batch):
            raise ValueError("Campi del batch non validi")
        batch_id = batch["id"]
        if (not isinstance(batch_id, str) or not re.fullmatch(r"[a-z0-9_]+", batch_id)
                or batch_id in batch_ids):
            raise ValueError("ID batch duplicato o non valido")
        batch_ids.add(batch_id)
        quantity = batch["per_scenario_modalita"]
        if type(quantity) is not int or quantity < 1:
            raise ValueError("Numerosità del batch non valida")
        selection = None if batch["scenari"] == "all" else batch["scenari"]
        if (selection is not None and (not isinstance(selection, list)
                or not selection or set(selection) - scenario_ids)):
            raise ValueError("Selezione scenari del batch non valida")
        modes = batch["modalita"]
        if not isinstance(modes, list):
            raise ValueError("Modalità del batch non valide")
        generated = list(genera(
            catalogo, quantity, seed + index, data_inizio, giorni, dati,
            selezione=selection, regole=regole,
            modalita_selezionate=modes,
            entita_obbligatorie=batch.get("entita_obbligatorie"),
            varianti_indirizzo=batch.get("varianti_indirizzo"),
            id_lotto=batch_id,
        ))
        for record in generated:
            record["seed"] = seed
            record["piano_generazione"] = {
                "versione": piano["versione"], "batch": batch_id,
                "seed_batch": seed + index,
            }
        records.extend(generated)
    if len(records) != piano["totale"] or len({record["id"] for record in records}) != len(records):
        raise ValueError(f"Il piano produce {len(records)} record invece di {piano['totale']}")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogo", type=Path, default=ROOT / "config/scenari.json")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--regole", type=Path, default=REGOLE_DEFAULT)
    parser.add_argument("--output", type=Path, default=ROOT / "output/prompts.jsonl")
    numerosita = parser.add_mutually_exclusive_group()
    numerosita.add_argument("--per-modalita", type=int, default=2, help="Prompt per scenario e modalità (default: 2)")
    numerosita.add_argument("--totale", type=int, help="Totale pari, distribuito per scenario e bilanciato fra le due modalità")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data-inizio", type=date.fromisoformat, default=date(2026, 4, 1))
    parser.add_argument("--giorni", type=int, default=21)
    parser.add_argument("--scenario", action="append", help="ID da includere; ripetibile")
    parser.add_argument("--piano", type=Path,
                        help="Piano stratificato; non combinare con --totale, --scenario o --per-modalita")
    args = parser.parse_args()
    if args.per_modalita < 1 or args.giorni < 1:
        parser.error("--per-modalita e --giorni devono essere positivi")
    try:
        if args.piano and (args.totale is not None or args.scenario or args.per_modalita != 2):
            raise ValueError("--piano non è combinabile con le opzioni di numerosità o scenario")
        catalogo = carica_scenari(args.catalogo)
        sconosciuti = set(args.scenario or []) - {s["id"] for s in catalogo["scenari"]}
        if sconosciuti:
            raise ValueError(f"Scenari sconosciuti: {', '.join(sorted(sconosciuti))}")
        if args.output.exists():
            raise ValueError(f"Output già esistente: {args.output}")
        dati = carica_input(args.data_dir)
        print(json.dumps(dati.statistiche, ensure_ascii=False))
        regole = carica_regole(args.regole)
        if args.piano:
            piano = json.loads(args.piano.read_text(encoding="utf-8"))
            righe = genera_da_piano(catalogo, piano, args.seed, args.data_inizio, args.giorni,
                                    dati, regole)
        else:
            righe = list(genera(catalogo, args.per_modalita, args.seed, args.data_inizio,
                                args.giorni, dati, args.scenario, regole, totale=args.totale))
        inputs = [args.data_dir / n for n in ("nomi.txt", "cognomi.txt", "codici_comuni.csv", "strade_lazio.csv", "codici_psn.csv")]
        provenance_files = inputs + [args.catalogo, args.regole] + ([args.piano] if args.piano else [])
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in provenance_files}
        for riga in righe:
            riga["provenienza_locale"] = {"specifica": "paper-address-1.0", "sha256_file": hashes}
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
