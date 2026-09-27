import os
def setup_proxy():
    os.environ['http_proxy'] = 'http://proxy.istat.it:8080'
    os.environ['https_proxy'] = 'http://proxy.istat.it:8080'


setup_proxy()

import json
from pathlib import Path
import re
import subprocess
import gc
import sys
import time
from transformers import AutoTokenizer, AutoModelForTokenClassification,pipeline
import pandas as pd  # Aggiunto per gestire l'Excel
import numpy
import shutil


# =========================================================
# Definizione delle cartelle di input e output
# =========================================================

# Definizione del percorso della cartella che contiene i file JSON di input
#cartella_input = Path("\\\\nas-istat.pc.istat.it\\chatbot_data\\raw")
cartella_input = Path("/anon_raccoldati/Files")

# Definizione del percorso della cartella che contiene i file JSON raw processati
cartella_processed = Path("/anon_raccoldati/processed")

# Definizione del percorso della cartella in cui salvare i file anonimizzati
cartella_output = Path("/anon_raccoldati/output_anon")



# =========================================================
# CARICAMENTO MODELLO NER (Fine-tuned BERT advanced)
# =========================================================

# Percorso aggiornato al tuo nuovo modello
model_path = "SamyPie/ner_model_fine_tuned_advanced"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForTokenClassification.from_pretrained(model_path)

ner = pipeline(
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple"
)



# =============================================================
# Funzione di anonimizzazione del testo (Regex)
# =============================================================
# Input:
#   testo (stringa) -> testo originale della conversazione utente
#                      nota: l'agente non usa PII
#
# Output:
#   testo anonimizzato con sostituzione delle PII

# L’ordine segue una logica precisa, per ridurre sovrascritture errate, falsi positivi e conflitti tra regex:
# Pattern altamente strutturati (email, IBAN, CF, password, account)
# Pattern numerici lunghezza maggiore di 5 cifre (telefono, PIVA)
# Pattern ambigui con contesto (id_utente, targa)
# Pattern più generici (date)

# =============================================================

def anonimizza_regex(testo):
    # ==================================================
    # EMAIL
    # ==================================================
    # Individua indirizzi email e li sostituisce con [EMAIL]
    # Esempio:
    # mario.rossi@gmail.com -> [EMAIL]
    # ==================================================

    testo = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL]', testo)

    # ==================================================
    # IBAN
    # ==================================================
    # IBAN italiano:
    # IT + 2 cifre + 1 lettera + 22 caratteri alfanumerici
    #
    # Gestisce anche IBAN con spazi
    #
    # Esempi:
    # IT60X0542811101000000123456 -> [IBAN]
    # IT60 X054 2811 1010 0000 0123 456 -> [IBAN]
    # ==================================================

    testo = re.sub(r'\bIT\d{2}[A-Z](?:\s?[A-Z0-9]){22}\b', '[IBAN]', testo)

    # ==================================================
    # CODICE FISCALE
    # ==================================================
    # Pattern del codice fiscale italiano (16 caratteri)
    # Esempio:
    # RSSMRA85M01H501Z -> [CF]
    #
    # ==================================================

    testo = re.sub(r'\b[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]\b', '[CF]', testo,
                   flags=re.IGNORECASE  # intercetta anche le versioni scritte in minuscolo
                   )

    # ==================================================
    # PROTOCOLLO
    # ==================================================
    # Intercetta il formato Prot.n. 1589563/25
    # ==================================================
    testo = re.sub(
        r'\b(Prot(?:\.|ocollo)?\s*n\.\s*)\d+(?:[\/\-]\d{2,4})\b',
        r'\1[NUM_PROT]',
        testo,
        flags=re.IGNORECASE
    )

    # ==================================================
    # PASSWORD
    # ==================================================
    # Intercetta password dichiarate esplicitamente
    # nel testo, precedute da parole chiave come:
    # "password", "pwd", "pass"
    #
    # Il valore della password deve:
    # - avere lunghezza minima di 8 caratteri
    # - contenere almeno una lettera
    # - contenere almeno un numero
    # - includere eventualmente simboli comuni
    #
    # Esempi:
    # password: crz5kne4i9     -> password: [PASSWORD]
    # pwd: abc12345            -> pwd: [PASSWORD]
    # Password = Abc!2345      -> password: [PASSWORD]
    #
    # NON intercetta:
    # password: abcdefgh       (solo lettere)
    # password: 12345678       (solo numeri)
    # password: abc            (troppo corta)
    #
    # Nota:
    # - Utilizza lookahead per vincolare la struttura
    # - Riduce i falsi positivi nei testi rumorosi
    # ==================================================

    testo = re.sub(
        r'\b(password|pwd|pass)\s*[:=]\s*(?=\S*[A-Za-z])(?=\S*\d)[A-Za-z0-9@#$%^&+=!?.]{8,}\b',
        r'\1: [PASSWORD]',
        testo,
        flags=re.IGNORECASE
    )
    # ==================================================
    # ID UTENTE (ACCOUNT + CODICE NUMERICO)
    # ==================================================
    # Intercetta identificativi utente in due forme:
    #
    # 1) ACCOUNT AMMINISTRATORE (PORTALE IMPRESE)
    #    Formato:
    #    P0 + 8 cifre
    #
    #    Esempi:
    #    P012345678 -> [ID_UTENTE]
    #
    # 2) ACCOUNT INDAGINI SULLE FAMIGLIE (GINO)
    #    Formato:
    #    QOL + almeno 5 cifre
    #
    #    Esempi:
    #    QOL123456789 -> [ID_UTENTE]
    #
    # 3) CODICE NUMERICO (CONTESTUALE)
    #    Sequenze di almeno 7 cifre, considerate ID utente
    #    solo se presenti in un contesto semantico coerente.
    #
    #    Parole chiave:
    #    "utente", "id", "codice", "cliente", "pratica"
    #
    #    Esempi:
    #    "codice utente 1234567"     -> [ID_UTENTE]
    #    "id 9876543210"             -> [ID_UTENTE]
    #
    # Problema:
    # Numeri lunghi possono rappresentare:
    # - telefoni
    # - date
    # - altri codici
    #
    # Soluzione:
    # - pattern specifico (P0...) gestito direttamente
    # - pattern numerico validato tramite contesto
    #
    # ==================================================

    # --- 1. ACCOUNT (P0 + 8 cifre) ---
    testo = re.sub(
        r'\bP0\d{8}\b',
        '[ID_UTENTE]',
        testo,
        flags=re.IGNORECASE
    )

    # --- 2. ACCOUNT (3lettere + almeno 5 cifre) ---
    testo = re.sub(
        r'\b[A-Z]{3}\d{5,}\b',
        '[ID_UTENTE]',
        testo,
        flags=re.IGNORECASE
    )

    # --- 3. CODICE NUMERICO CONTESTUALE ---
    pattern_id = re.compile(r'\b\d{7,}\b')

    pattern_contesto_id = re.compile(
        r'\b(utente|id|codice|username|codice utente|cod utente|cod. utente|cod)\b',
        re.IGNORECASE
    )

    nuovo_testo = testo
    offset = 0

    for match in pattern_id.finditer(testo):
        start, end = match.span()
        window = testo[max(0, start - 20):min(len(testo), end + 20)]

        if pattern_contesto_id.search(window):
            nuovo_testo = nuovo_testo[:start + offset] + "[ID_UTENTE]" + nuovo_testo[end + offset:]
            offset += len("[ID_UTENTE]") - (end - start)
    # Aggiorna il testo con le eventuali sostituzioni
    # degli identificativi numerici contestuali
    testo = nuovo_testo

    # ==================================================
    # PARTITA IVA
    # ==================================================
    # La partita IVA italiana è composta da 11 cifre
    #
    # Esempio:
    # 12345678901 -> [PIVA]
    # ==================================================

    testo = re.sub(r'\b\d{11}\b', '[PIVA]', testo)

    # ==================================================
    # NUMERI DI TELEFONO
    # ==================================================
    # Intercetta numeri di telefono italiani con o senza spazi:
    # - con prefisso internazionale (+39)
    # - senza prefisso
    # - spazi opzionali tra i blocchi di cifre
    #
    # Esempi:
    # +39 3331234567
    # +39 333 123 4567
    # 3331234567
    # 333 123 4567
    # 06 4673.2222 da aggiungere
    # ==================================================

    testo = re.sub(r'\b(\+39\s?)?(?:\d{2,4}[\s.]?\d{3,4}[\s.]?\d{3,4})\b', '[NUMERO]', testo)

    # ==================================================
    # TARGA VEICOLO (CONTESTUALE)
    # ==================================================
    # Le targhe italiane moderne hanno formato:
    # AA123BB (con possibili varianti con spazi o trattini)
    #
    # Problema:
    # Pattern simili possono comparire come codici
    #
    # Soluzione:
    # Sostituzione SOLO se vicino a parole chiave (targa, auto, veicolo, ecc.)
    # Es.
    # Input:"La targa del veicolo è AB123CD"
    # Output:"La targa del veicolo è [TARGA]"
    # Input:"Il codice AB123CD è errato"
    # Output:"Il codice AB123CD è errato"   # non sostituito (manca contesto)

    # ==================================================

    pattern_targa = re.compile(r'\b[A-Z]{2}[\s\-]?\d{3}[\s\-]?[A-Z]{2}\b')

    pattern_contesto = re.compile(
        r'\b(targa|auto|veicolo|camion|automezzo|mezzo|macchina|furgone|moto|motorino|tir)\b',
        re.IGNORECASE
    )

    for match in pattern_targa.finditer(testo):
        start, end = match.span()

        window = testo[max(0, start - 20):min(len(testo), end + 20)]

        if pattern_contesto.search(window):
            testo = testo.replace(match.group(), "[TARGA]")

    # ==================================================
    # DATE (es. data di nascita)
    # ==================================================
    # Individua date scritte nei seguenti formati numerici:
    # - 12/05/1985
    # - 12-05-1985
    # - 12 05 1985
    # - 12 05 85
    # - 12051985
    # - 051985 #
    # e le sostituisce con [DATA]
    # ==================================================

    testo = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[DATA]', testo)

    # ==================================================
    # Individua date scritte nei seguenti formati testuali:
    # - 12 maggio 2024
    # - 5 mar 23
    # - 1 gennaio 23
    # - set 2022
    #
    # e le sostituisce con [DATA]
    # ==================================================

    testo = re.sub(
        r'\b\d{1,2}\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre|gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\s*(\d{2,4})?\b',
        '[DATA]',
        testo,
        flags=re.IGNORECASE  # intercetta anche le versioni scritte in minuscolo
    )

    return testo

placeholders = [
    "[EMAIL]", "[IBAN]", "[CF]", "[PASSWORD]", "[ID_UTENTE]",
    "[PIVA]", "[NUMERO]", "[TARGA]", "[DATA]", "[ADDRESS]", "[NAME]", "[NUM_PROT]"
]
#funzione per verificare overlap con i placeholders
def is_inside_placeholder(text, start, end):
    for ph in placeholders:
        idx = text.find(ph)
        while idx != -1:
            ph_start = idx
            ph_end = idx + len(ph)

            # overlap tra entity e placeholder
            if not (end <= ph_start or start >= ph_end):
                return True

            idx = text.find(ph, idx + 1)
    return False
def anonimizza_bert(testo):
    try:
        entities = ner(testo)
        entities = sorted(entities, key=lambda x: x['start'])

        risultato = []
        last_idx = 0

        for ent in entities:
            start = ent['start']
            end = ent['end']
            label = ent.get("entity_group", None)
            entity_text = testo[start:end]

            risultato.append(testo[last_idx:start])

            # =========================
            # FILTRO PLACEHOLDER
            # =========================
            if is_inside_placeholder(testo, start, end):
                risultato.append(entity_text)
                last_idx = end
                continue

            # =========================
            # FILTRI LEGGERI MA EFFICACI
            # =========================

            # 1. Confidence
            if ent["score"] < 0.7:
                risultato.append(entity_text)
                last_idx = end
                continue

            # 2. Lunghezza minima
            if len(entity_text.strip()) < 3:
                risultato.append(entity_text)
                last_idx = end
                continue

            # =========================
            # SOSTITUZIONE
            # =========================

            # Adattato ai tag NAME e ADDRESS del nuovo modello
            if label in ["NAME", "PER"]:
                risultato.append("[NAME]")
            elif label in ["ADDRESS", "LOC"]:
                risultato.append("[ADDRESS]")
            else:
                risultato.append(entity_text)

            last_idx = end

        risultato.append(testo[last_idx:])

        testo_finale = "".join(risultato)

        # cleanup
        testo_finale = re.sub(r'\[NAME\]{2,}', '[NAME]', testo_finale)
        testo_finale = re.sub(r'\[ADDRESS\]{2,}', '[ADDRESS]', testo_finale)

        testo_finale = collapse_addresses(testo_finale)

        return testo_finale


    except Exception as e:

        print("Errore BERT:", e)

        return testo

def collapse_addresses(text):
    """
    Collassa sequenze multiple di [ADDRESS] e contenuti intermedi
    in un unico [ADDRESS]
    """

    text = re.sub(r'\s+', ' ', text)

    pattern = r'(\[ADDRESS\](\s*[,;.-]?\s*(\d{4,5})?\s*)+\[ADDRESS\])'
    text = re.sub(pattern, '[ADDRESS]', text)

    text = re.sub(r'(\[ADDRESS\]\s*){2,}', '[ADDRESS] ', text)

    text = re.sub(r'\s+', ' ', text).strip()

    return text

# =========================================================
# PROCESSAMENTO FILE JSON
# =========================================================
tempi = []

def processa_file(file_json):
    output_file = cartella_output / file_json.name

    try:
        with open(file_json, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        print("🔎 Conversazioni:", len(data))

        total_msgs = 0
        total_utenti = 0

        for conv in data:
            for msg in conv.get("Conversazione", []):
                total_msgs += 1
                if msg.get("Sender"):
                    if "utent" in msg.get("Sender", "").lower():
                        total_utenti += 1

        print("📊 Messaggi totali:", total_msgs)
        print("👤 Messaggi utente trovati:", total_utenti)

        for conv_idx, conv in enumerate(data):
            for msg_idx, msg in enumerate(conv.get("Conversazione", [])):
                if msg.get("Testo"): #per anonimizzare anche i testi del chatbot
                    testo = anonimizza_regex(msg["Testo"])  # regex prima di BERT
                    testo = anonimizza_bert(testo)
                    msg["Testo"] = testo

        # ===== SAVE =====
        with open(output_file, "w", encoding="utf-8-sig") as f_out:
            json.dump(data, f_out, ensure_ascii=False, indent=2)

        print(f"✅ Processato: {file_json.name}")
        
        # Sposta il file originale nella cartella processed
        cartella_processed.mkdir(parents=True, exist_ok=True)

        destinazione = cartella_processed / file_json.name
        if destinazione.exists():
            print(f"⚠️ File già presente in processed: {file_json.name}")
        else:
            shutil.move(str(file_json), str(destinazione))
            print(f"📦 Spostato in processed: {file_json.name}")

    except Exception as e:
        print(f"❌ Errore in {file_json.name}: {e}")

    finally:
        del data
        gc.collect()


# =========================================================
# Ciclo sui tutti i file JSON
# =========================================================

if __name__ == "__main__":
    for file_json in cartella_input.glob("*.json"):
        print(f"📂 Sto processando: {file_json.name}")
        processa_file(file_json)



def hybrid_anonymize(text):
    """Funzione helper che unisce i due step"""
    text_regex = anonimizza_regex(text)
    return anonimizza_bert(text_regex)


# =========================================================
# NUOVA FUNZIONE: GENERAZIONE GOLD STANDARD (Parallel Corpus)
# =========================================================

def prepare_parallel_corpus(file_list, sample_limit=None):
    """
    Legge i JSON reali, applica il sistema ibrido e crea un Excel
    per la validazione umana (Gold Standard).
    """
    dataset_rows = []
    print(f"🛠 Generazione Parallel Corpus per {len(file_list)} file...")

    for file_path in file_list:
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)

            # Estrazione messaggi dai tuoi JSON annidati
            for conv in data:
                for msg in conv.get("Conversazione", []):
                    original_text = msg.get("Testo", "").strip()
                    if original_text and len(original_text) > 5:  # Filtra messaggi vuoti o troppo corti

                        # Esegui l'anonimizzazione ibrida (Regex + BERT)
                        automated_anon = hybrid_anonymize(original_text)

                        dataset_rows.append({
                            "Source_File": file_path.name,
                            "Original_Text": original_text,
                            "System_Anonymized": automated_anon,
                            "Gold_Standard_Correction": ""  # Colonna da compilare a mano se il sistema sbaglia
                        })

                        if sample_limit and len(dataset_rows) >= sample_limit:
                            break
                if sample_limit and len(dataset_rows) >= sample_limit:
                    break
        except Exception as e:
            print(f"❌ Errore nel file {file_path.name}: {e}")

    # Creazione del DataFrame e salvataggio
    df = pd.DataFrame(dataset_rows)
    output_excel = "Gold_Standard_Validation_JADT.xlsx"
    df.to_excel(output_excel, index=False)
    print(f"✅ File di verifica creato: {output_excel}")
    print(
        f"👉 Istruzioni: Apri il file e correggi 'System_Anonymized' nella colonna 'Gold_Standard_Correction' solo dove ci sono errori.")


# =========================================================
# ESECUZIONE (LOGICA DI LANCIO)
# =========================================================

if __name__ == "__main__":
    # 1. Recupero lista file
    tutti_i_file = list(cartella_input.glob("*.json"))

    # --- OPZIONE A: PROCESSO MASSIVO
    for file_json in tutti_i_file:
        print(f"📂 Sto processando: {file_json.name}")
        processa_file(file_json)

    # --- OPZIONE B: GENERAZIONE FILE PER GOLD STANDARD (COMMENTATO) ---
    # Selezioniamo, ad esempio, i due file più grandi
    # --- NUOVA LOGICA: Ordinamento per dimensione decrescente ---
    # Usiamo os.path.getsize per ottenere il peso in byte di ogni file
    #tutti_i_file.sort(key=lambda x: os.path.getsize(x), reverse=True)

    # 2. Selezioniamo i due file più grandi
   # file_target = tutti_i_file[:2]

   # print("📊 File selezionati per il Gold Standard (i più grandi):")
    #for f in file_target:
    #    dimensione_mb = os.path.getsize(f) / (1024 * 1024)
     #   print(f" - {f.name} ({dimensione_mb:.2f} MB)")


    # Lanciamo la creazione dell'Excel per il test sui dati reali
    # sample_limit=200 estrae solo i primi 200 messaggi per rendere la validazione umana fattibile
   # prepare_parallel_corpus(file_target, sample_limit=300)