"""Validazione locale e annotazioni; nessuna dipendenza dal client API."""

import copy
import re

from annotazioni import sostituisci_con_span

def valida(chat, scheda):
    """Controlli strutturali e sui vincoli espliciti; non una revisione semantica."""
    if not isinstance(chat, dict) or set(chat) != {"metadati", "conversazione", "trattamento_atteso"}:
        raise ValueError("Campi principali della risposta non validi")
    meta = chat["metadati"]
    campi = {"data_sintetica", "chiave_indagine", "descrizione"}
    # I lotti storici restano rivalidabili senza riscriverne il formato.
    if "canale" in scheda["metadati_fissati"]:
        campi.add("canale")
    if not isinstance(meta, dict) or set(meta) != campi:
        raise ValueError("Metadati non validi")
    if any(meta.get(k) != v for k, v in scheda["metadati_fissati"].items()):
        raise ValueError("Il modello ha modificato i metadati fissati")
    if not isinstance(meta["descrizione"], str) or not meta["descrizione"].strip():
        raise ValueError("Descrizione mancante")
    messaggi = chat["conversazione"]
    if not isinstance(messaggi, list) or len(messaggi) < 2:
        raise ValueError("La conversazione deve contenere almeno una domanda e una risposta")
    for i, msg in enumerate(messaggi):
        if (not isinstance(msg, dict) or set(msg) != {"sender", "testo"}
                or msg["sender"] != ("Utente" if i % 2 == 0 else "Agente")
                or not isinstance(msg["testo"], str) or not msg["testo"].strip()):
            raise ValueError("Messaggio o alternanza dei ruoli non validi")
    entita = {e["segnaposto"]: e for e in scheda["entita_previste"]}
    if len(entita) != len(scheda["entita_previste"]):
        raise ValueError("Segnaposto duplicati nella scheda")
    modalita = scheda.get("modalita")
    if modalita in {"con_dati_personali", "senza_dati_personali"} and bool(entita) != (modalita == "con_dati_personali"):
        raise ValueError("Entità incompatibili con la modalità")
    dialogo = "\n".join(m["testo"] for m in messaggi)
    testo = dialogo + "\n" + meta["descrizione"]
    trovati = set(re.findall(r"\{\{[^{}]+\}\}", testo))
    if trovati != set(entita) or any(p not in dialogo for p in entita):
        raise ValueError("Segnaposto mancanti o non previsti")
    if any(e["valore_proposto"] in testo for e in entita.values()):
        raise ValueError("Il modello ha scritto un valore al posto del segnaposto")
    trattamento = chat["trattamento_atteso"]
    if not isinstance(trattamento, dict) or set(trattamento) != {"mascherare", "conservare", "motivazione"}:
        raise ValueError("Trattamento atteso non valido")
    attesi = [{k: e[k] for k in ("segnaposto", "tipo", "sostituzione")} for e in entita.values()]
    mascherare = trattamento["mascherare"]
    if not isinstance(mascherare, list) or len(mascherare) != len(attesi) or any(e not in mascherare for e in attesi):
        raise ValueError("Annotazioni delle entità non coerenti")
    if (not isinstance(trattamento["conservare"], list)
            or not all(isinstance(v, str) for v in trattamento["conservare"])
            or not isinstance(trattamento["motivazione"], str)):
        raise ValueError("Spiegazioni del trattamento non valide")


def sostituisci(valore, mappa):
    if isinstance(valore, str):
        return re.sub(r"\{\{[^{}]+\}\}", lambda m: mappa.get(m[0], m[0]), valore)
    if isinstance(valore, list):
        return [sostituisci(v, mappa) for v in valore]
    if isinstance(valore, dict):
        return {k: sostituisci(v, mappa) for k, v in valore.items()}
    return valore


def controlla_coerenza(chat):
    """Segnali lessicali da revisionare, non una verifica semantica generale."""
    riepilogo = (chat["metadati"]["descrizione"] + " " +
                 " ".join(chat["trattamento_atteso"]["conservare"])).casefold()
    # Una domanda del chatbot con possibili stati non conferma lo stato reale.
    dichiarazioni = " ".join(m["testo"] for m in chat["conversazione"]
                             if m["sender"] == "Utente").casefold()
    segnali = []
    for stato in ("in compilazione", "in bozza", "in sola lettura"):
        if stato in riepilogo and stato not in dichiarazioni:
            segnali.append(f"Stato '{stato}' nel riepilogo ma non dichiarato dall'utente: verificare")
    return segnali


def prepara_chat(chat, scheda):
    """Normalizza solo alias inequivocabili, poi applica tutti i controlli."""
    chat = copy.deepcopy(chat)
    correzioni = []
    if isinstance(chat, dict) and isinstance(chat.get("conversazione"), list):
        for i, msg in enumerate(chat["conversazione"]):
            if isinstance(msg, dict) and "text" in msg and "testo" not in msg:
                msg["testo"] = msg.pop("text")
                correzioni.append(f"Messaggio {i + 1}: text rinominato in testo")
        # Rimuove solo un vuoto interno seguito dallo stesso ruolo non vuoto.
        # Non rimuove vuoti finali né inventa risposte mancanti.
        messaggi = chat["conversazione"]
        puliti = []
        for i, msg in enumerate(messaggi):
            prossimo = messaggi[i + 1] if i + 1 < len(messaggi) else None
            if (isinstance(msg, dict) and set(msg) == {"sender", "testo"}
                    and isinstance(msg["testo"], str) and not msg["testo"].strip()
                    and isinstance(prossimo, dict) and prossimo.get("sender") == msg["sender"]
                    and isinstance(prossimo.get("testo"), str) and prossimo["testo"].strip()):
                correzioni.append(f"Messaggio {i + 1}: rimosso vuoto interno prima dello stesso ruolo")
            else:
                puliti.append(msg)
        chat["conversazione"] = puliti
    valida(chat, scheda)
    segnali = controlla_coerenza(chat)
    effettivi = len(chat["conversazione"]) // 2
    avvisi = []
    if effettivi != scheda["numero_scambi"]:
        avvisi.append(f"Scambi desiderati: {scheda['numero_scambi']}; effettivi: {effettivi}")
    concreta = copy.deepcopy(chat)
    if "canale" in scheda["metadati_fissati"]:
        mappa = {e["segnaposto"]: e["valore_proposto"] for e in scheda["entita_previste"]}
        for campo in ("metadati", "conversazione"):
            concreta[campo] = sostituisci(chat[campo], mappa)
    else:
        spans = []
        for indice, messaggio in enumerate(chat["conversazione"]):
            testo, occorrenze = sostituisci_con_span(messaggio["testo"], scheda["entita_previste"], f"conversazione.{indice}.testo")
            concreta["conversazione"][indice]["testo"] = testo
            spans.extend(occorrenze)
        testo, occorrenze = sostituisci_con_span(chat["metadati"]["descrizione"], scheda["entita_previste"], "metadati.descrizione")
        concreta["metadati"]["descrizione"] = testo
        spans.extend(occorrenze)
        concreta["trattamento_atteso"]["mascherare"] = spans
        # Le spiegazioni possono ripetere slot: concretizzarli e annotarli anche qui.
        trattamento = concreta["trattamento_atteso"]
        for indice, spiegazione in enumerate(trattamento["conservare"]):
            testo, extra = sostituisci_con_span(spiegazione, scheda["entita_previste"], f"trattamento_atteso.conservare.{indice}")
            trattamento["conservare"][indice] = testo
            spans.extend(extra)
        testo, extra = sostituisci_con_span(trattamento["motivazione"], scheda["entita_previste"], "trattamento_atteso.motivazione")
        trattamento["motivazione"] = testo
        spans.extend(extra)
    return {
        "chat_template": chat, "chat": concreta,
        "stato": "da_verificare" if segnali else "valido",
        "validazione": {"versione": "3.0", "ambito": "strutturale_con_segnali_di_coerenza",
                        "segnali_coerenza": segnali,
                        "correzioni": correzioni, "avvisi": avvisi,
                        "scambi_effettivi": effettivi,
                        "messaggi_totali": len(chat["conversazione"]),
                        "chiusura_utente": chat["conversazione"][-1]["sender"] == "Utente"},
    }

