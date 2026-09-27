import random
import pandas as pd
from tqdm import tqdm
from pathlib import Path
import re

# Configurazione percorsi
file_path = Path(r"C:\Users\pietropaoli\OneDrive - ISTAT\RDM 2025\CHATBOT")
output_path = Path(r"\\nas-istat.pc.istat.it\chatbot_data\conll\dataset_conll_advanced.txt")

# =========================================================
# 1. CARICAMENTO DATI E PRE-OTTIMIZZAZIONE
# =========================================================

print("📥 Caricamento basi dati...")

# Nomi e Cognomi
with open(file_path / 'nomi_italiani.txt', 'r', encoding='utf-8') as f:
    names_list = [line.strip() for line in f if line.strip()]

with open(file_path / 'cognomi.txt', 'r', encoding='utf-8') as f:
    surnames_list = [line.strip() for line in f if line.strip()]

# Comuni
df_comuni = pd.read_csv(file_path / 'comuni_istat_2026.csv', sep=';', encoding='utf-8')
cities_list = df_comuni['Comune'].dropna().tolist()

# Indirizzi (Odonimi)
df_indir = pd.read_csv(
    file_path / 'INDIR_ITA_20260406.csv',
    sep=';',
    encoding='utf-8',
    dtype=str,
    low_memory=False
)

num_samples = 3000

print(f"📦 Pre-estrazione di {num_samples} indirizzi per ottimizzare le prestazioni...")
# Estraiamo un blocco di righe casuali tutto in una volta
random_rows = df_indir.sample(num_samples, replace=True)
precomputed_streets = []

for _, row in random_rows.iterrows():
    opzioni = [row['ODONIMO']]
    if pd.notna(row['DIZIONE_LINGUA1']): opzioni.append(row['DIZIONE_LINGUA1'])
    if pd.notna(row['DIZIONE_LINGUA2']): opzioni.append(row['DIZIONE_LINGUA2'])
    precomputed_streets.append(random.choice(opzioni))

# =========================================================
# 2. FUNZIONI DI GENERAZIONE VELOCI
# =========================================================

def generate_full_name():
    return f"{random.choice(names_list)} {random.choice(surnames_list)}"

def generate_complex_address(idx):
    street_name = precomputed_streets[idx]
    number = random.randint(1, 300)
    city = random.choice(cities_list)

    formats = [
        f"{street_name} {number}, {city}",
        f"{street_name} {number} {city}",
        f"{street_name}, {city}"
    ]
    return random.choice(formats)

def to_conll(sentence, name, address):
    # 1. Stacchiamo la punteggiatura dai bordi per facilitare il matching
    sentence = re.sub(r'([.,!?()])', r' \1 ', sentence)
    tokens = sentence.split()

    # Prepariamo le parti da cercare nello stesso modo
    name_parts = re.sub(r'([.,!?()])', r' \1 ', name).split() if name else []
    address_parts = re.sub(r'([.,!?()])', r' \1 ', address).split() if address else []

    result = []
    i = 0
    while i < len(tokens):
        # Match NAME
        if name_parts and tokens[i:i + len(name_parts)] == name_parts:
            for j in range(len(name_parts)):
                tag = "B-NAME" if j == 0 else "I-NAME"
                result.append(f"{tokens[i + j]} {tag}")
            i += len(name_parts)
        # Match ADDRESS
        elif address_parts and tokens[i:i + len(address_parts)] == address_parts:
            for j in range(len(address_parts)):
                tag = "B-ADDRESS" if j == 0 else "I-ADDRESS"
                result.append(f"{tokens[i + j]} {tag}")
            i += len(address_parts)
        else:
            result.append(f"{tokens[i]} O")
            i += 1
    return "\n".join(result)

# =========================================================
# 3. PATTERNS
# =========================================================

patterns = [
    "salve sono {name} e abito in {address}",
    "mi chiamo {name} residente in {address}",
    "ciao sono {name} vivo in {address}",
    "buongiorno sono {name} e risiedo in {address}",
    "sono {name} e il mio indirizzo è {address}",
    "io mi chiamo {name} e abito a {address}",
    "sn {name} abito {address}",
    "io {name} via {address}",
    "sono {name} {address}",
    "abito in {address} sono {name}",
    "mi chiamo {name} {address}",
    "dammi le credenziali per compilare il questionario imprese intestato a me {name}",
    "buongiorno, è arrivata comunicazione di compilare questionario del CINEMA SRL al vecchio presidente {name}",
    "sono residente nel comune di {address} che deve rispondere al censimento",
    "Buongiorno. Da Comune di {address} uff. Statistica invito a contattare {name}",
    "salve sono {name} amministratore della società con sede in {address}",
    "ho bisogno di aiuto, mi chiamo {name}",
    "Il Comune è: {address} - Provincia di {address} (LO)",
    "Quante con il nome {name} esistono in Italia ?",
    "Andamento presenze turistiche comune di {address}",
    "Buongiorno, sono dipendente del Comune di {address} (PD) dal febbraio 2025",
    "qual'è il numero o l'indirizzo del centro comunale di rilevazione di {address}",
    "sono andata in comune (abito a {address})",
    "Come posso fare questo questionario tramite intervista telefonica? Perché al momento non vivo più in {address}",
    "come faccio a entrare visto che non ho piu le credenziali : CLIMAT S.N.C. DI {name} E {name} {address}",
    "mostrami i dati per il turismo nel comune di {address}",
    "sapere che tipo di censimento è in corso nella città di {address} cap {address}?",
    "nel link non compare il tipo di censimentto, ma l'indirizzo e il telefono del comune di {address}, io vorrei il questionario da compilare on line",
    "Come posso fare questo questionario tramite intervista telefonica? Perché al momento non vivo nel comune {address} in {address}",
    "studenti del Liceo G. Cesare-M. Valgimigli di {address}, i sottoscritti {name} e {name}, ambi residenti a {address}, saremmo entusiasti di ricevere grafici dettagliati",
    # Falsi Positivi
    "non riesco ad accedere al sito",
    "vorrei sapere quando scade il censimento",
    "ho perso la lettera con le credenziali",
    "non ricordo la password",
    "ho smarrito le credenziali di accesso",
    "Chiave indagine 02623",
    "Cancellazione nominativo dal censimento",
    "Come posso fare per resettare",
    "QUINDI NON COMPILERò PIù NULLA D'ORA IN AVANZTI?",
    "è ricoverata in RSA ed è incapace di intendere e rispondere",
    "È arrivata una lettera al mio indirizzo ma non è a mio nome cosa devo fare?",
    "Dove posso indicare il cambio di residenza?",
    "misono trasferito in una ltro comune ma posso rispondere?"
]

# =========================================================
# 4. LOOP DI GENERAZIONE
# =========================================================

dataset = []
print(f"🚀 Generazione di {num_samples} frasi in corso...")

for i in tqdm(range(num_samples)):
    name = generate_full_name()
    address = generate_complex_address(i) # Uso dell'indice per velocità

    # --- AGGIUNTA VARIETÀ CASE ---
    dice = random.random()
    if dice > 0.7:
        name = name.title()  # Mario Rossi
        address = address.title()  # Via Roma 12, Milano
    elif dice > 0.4:
        name = name.lower()  # mario rossi
        address = address.lower()  # via roma 12, milano
    # Altrimenti (30% dei casi) resta MAIUSCOLO come da database originale
    # -----------------------------

    pat = random.choice(patterns)

    # Riempiamo i placeholder se presenti
    if "{name}" in pat or "{address}" in pat:
        sentence = pat.format(name=name, address=address)
    else:
        sentence = pat
        name, address = "", "" # Per to_conll: nessuna entità da cercare

    conll_sentence = to_conll(sentence, name, address)
    dataset.append(conll_sentence)

# Salvataggio finale
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n\n".join(dataset))

print(f"✅ DONE! Dataset salvato in: {output_path}")


'''
VECCHIO CODICE
import random

patterns = [
    "salve sono {name} e abito in {address}",
    "mi chiamo {name} residente in {address}",
    "ciao sono {name} vivo in {address}",
    "buongiorno sono {name} e risiedo in {address}",
    "sono {name} e il mio indirizzo è {address}",
    "io mi chiamo {name} e abito a {address}",
    "sn {name} abito {address}",
    "io {name} via {address}",
    "sono {name} {address}",
    "abito in {address} sono {name}",
    "mi chiamo {name} {address}",
    "dammi le credenziali per compilare il questionario imprese intestato a me {name}",
    "buongiorno, è arrivata comunicazione di compilare questionario del CINEMA SRL al vecchio presidente {name} ",
    "sono residente nel comune di {address} che deve rispondere al censimento, ma non ho ricevuto la lettera via posta",
    "ciao sono {name} e sto parlando con te solo per fare un test",
    "ciao sono {name}",
    "Buongiorno. Da Comune di {address} uff. Statistica/Anagrafe invito a compilare questionario obbligatorio del Censimento popolazione. Si può accedere con credenziali Spid o carta d?identità elettronica del capo famiglia, dalla pagina Istat ? In alternativa contattare {name},rilevatrice Istat. Per info: uff anagrafe.Grazie. Cordiali Saluti.",
    "salve sono {name} amministratore della Di Carlo Gioielli Group Srl ho necessità di recuperare la password ma inserendo le credenziali 021034158 amministrazione@dicarlogioielli.com mi da errore",
    "Salve sono {name} devo compilare il censimento ma le chiavi che mi sono date nome utente P006870284 la password mi da errore , ho provato a recuperarla ma mi dice che ce un errore , ho gia inviato mail di sollecito ma nessuno mi risponde"
    "salve sono {name} non ricordo le credenziali per accedere al sistema",
    "salve , mi chiamo {name}",
    "sto registrando il mio nome, mi chiamo {name}, però mi dice che il mio nome non è  valido",
    "come posso effettuare il login, mi chiamo {name}",
    "non ricordo la password per entrare ,il mio nome è {name}"
]

names = [
    "Mario Rossi", "Luca Bianchi", "Giulia Verdi", "Anna Ferrari",
    "Marco Esposito", "Francesca Romano", "Alessandro Greco",
    "Simone Bruno", "Roberta Gallo", "Davide Conti",
    "Antonio Di Carlo", "Riccardo Leone"
]

streets = ["slargo","sottopasso","sovrappasso","spiazzo", "strada","strada antica",
    "strada comunale","strada consortile","strada nuova","strada panoramica",
    "cortile", "strada poderale","discesa", "strada privata","galleria",
    "strada provinciale","gradinata","strada regionale","larghetto",
    "strada statale","largo","strada vecchia", "litoranea","Via", "Corso", "Viale", "Piazza", "piazzale"
]

street_names = [
    "Roma", "Garibaldi", "Cavour", "Mazzini", "Manzoni",
    "Marconi", "Dante", "Verdi", "Carducci", "Giuseppe Bianchi"
]

cities = [
    "Roma", "Milano", "Torino", "Napoli", "Bologna", "Firenze","Palermo","Aosta","Bolzano","Pescara", "Sant'Agata de' Goti","San Marino"
]
def generate_address():
    street = random.choice(streets)
    street_name = random.choice(street_names)
    number = random.randint(1, 200)
    city = random.choice(cities)

    return f"{street} {street_name} {number} {city}"


def to_conll(sentence, name, address):
    tokens = sentence.split()
    name_parts = name.split()
    address_parts = address.split()

    result = []
    i = 0

    while i < len(tokens):

        # match NAME
        if tokens[i:i + len(name_parts)] == name_parts:
            for j, part in enumerate(name_parts):
                tag = "B-NAME" if j == 0 else "I-NAME"
                result.append(f"{part} {tag}")
            i += len(name_parts)

        # match ADDRESS
        elif tokens[i:i + len(address_parts)] == address_parts:
            for j, part in enumerate(address_parts):
                tag = "B-ADDRESS" if j == 0 else "I-ADDRESS"
                result.append(f"{part} {tag}")
            i += len(address_parts)

        else:
            result.append(f"{tokens[i]} O")
            i += 1

    return "\n".join(result)


dataset = []

for _ in range(500):
    name = random.choice(names)
    address = generate_address()

    sentence = random.choice(patterns).format(name=name, address=address)
    conll = to_conll(sentence, name, address)

    dataset.append(conll)

with open(r"\\nas-istat.pc.istat.it\chatbot_data\conll\dataset_conll.txt", "w", encoding="utf-8") as f:
    f.write("\n\n".join(dataset))

print("Dataset generato con NAME + ADDRESS!")
'''