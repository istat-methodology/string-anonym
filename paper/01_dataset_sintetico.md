# Costruzione del dataset sintetico

## Obiettivo

Il dataset è stato costruito per valutare in modo riproducibile la detection di
elementi identificativi in conversazioni di assistenza istituzionale. L'uso di
dati sintetici consente di controllare le entità inserite e i relativi offset
senza esporre conversazioni reali. Il corpus è uno strumento di sviluppo e di
stress test: non vuole riprodurre la prevalenza delle categorie nel traffico
operativo e non sostituisce un test indipendente su dati reali.

## Scenari e piano di campionamento

Il catalogo contiene 12 scenari derivati dall'analisi di conversazioni
anonimizzate del chatbot. Il piano versionato suddivide i 300 prompt in tre
batch:

| Batch | Conversazioni previste | Funzione |
| --- | ---: | --- |
| `general_core` | 230 | dieci esempi per ogni combinazione scenario–modalità disponibile |
| `general_extra` | 10 | riequilibrio di cinque scenari centrali |
| `address_focus` | 60 | stress test mirato degli indirizzi |
| **Totale** | **300** | |

La distribuzione dei prompt è 175 conversazioni con dati personali e 125 senza.
I dati personali sono valori sintetici; nomi, cognomi, strade e comuni sono
campionati da cataloghi locali, mentre civici, interni, telefoni, credenziali e
identificativi strutturati sono generati secondo regole versionate. I codici PSN
e i nomi delle indagini provengono dal catalogo di progetto e non sono inventati
dal modello generativo.

## Generazione controllata

La generazione separa tre responsabilità:

1. il codice sceglie scenario, modalità, stile, valori proposti e riferimenti
   pubblici da conservare;
2. il modello produce soltanto il dialogo, usando segnaposto autorizzati per le
   entità personali;
3. il codice sostituisce gli slot con i valori sintetici, calcola gli offset e
   costruisce il gold di detection.

Il modello non produce annotazioni, decisioni di masking o valutazioni. Questa
separazione evita che il generatore decida direttamente ciò che verrà poi
considerato corretto nel benchmark. Prompt, seed, versione delle regole e hash
SHA-256 delle sorgenti vengono conservati per controllare la riproducibilità.
La versione usata è `5.1-address`; il piano è
`paper-300-address-1.0`.

Ogni chat deve iniziare con l'utente, alternare i ruoli, terminare con l'Agente
e contenere almeno tre scambi completi. I controlli locali verificano inoltre
schema JSON, slot, riferimenti richiesti, offset e alcuni segnali espliciti di
coerenza. Questi controlli non equivalgono a una revisione semantica umana.

## Stress test degli indirizzi

Il batch mirato assegna dieci prompt a ciascuna delle sei forme:

| Variante | Forma schematica | Componenti |
| --- | --- | --- |
| Completo standard | `Via Angelo Lauri 96, Anzio` | tipo, strada, civico, comune |
| Senza tipo di strada | `Angelo Lauri 96, Anzio` | strada, civico, comune |
| Senza civico | `Via Angelo Lauri, Anzio` | tipo, strada, comune |
| Senza comune | `Via Angelo Lauri 96` | tipo, strada, civico |
| Civico complesso | `Via Angelo Lauri 96/A, Anzio` | strada, civico ed estensione, comune |
| Con interno | `Via Angelo Lauri 96, interno 4, Anzio` | strada, civico, interno, comune |

Oltre ai 60 prompt mirati, il campionamento generale contiene 13 schede con un
indirizzo. Il prompt impone che lo slot `ADDRESS` rappresenti l'intera forma
superficiale: parole come “via”, “civico” o “interno” non possono essere
aggiunte fuori dallo slot, perché sfuggirebbero al gold.

Ogni indirizzo conserva componenti strutturate (`street_type`, `street_name`,
`house_number`, eventuale estensione, `internal` e `municipality`) con offset
locali. Dopo la sostituzione, gli offset vengono traslati nel messaggio. Queste
componenti servono a costruire e valutare il gold; non diventano nuove classi
richieste ai modelli NER.

## Controllo qualità ed esportazione

La generazione ha prodotto 300 conversazioni. Il controllo qualità ne ha
validate 289 (96,3%) ed escluse 11 per violazioni strutturali o segnali di
coerenza; nessuna esclusione deriva da un errore API. Le conversazioni escluse
sono conservate con la motivazione e non entrano nelle metriche. Non sono state
corrette manualmente o promosse a valide per raggiungere una numerosità
prefissata.

L'esportatore produce file distinti:

- `input.jsonl`, con soli ruoli e testi per i modelli;
- `detections_attese.jsonl`, gold canonico con provenienza e overlap;
- `annotazioni_ner_attese.jsonl`, vista `PERSON`–`LOCATION`;
- `provenienza.jsonl`, `esclusi.jsonl` e `manifest.json` per la tracciabilità.

Il benchmark risultante contiene 289 conversazioni, 123 annotazioni `PERSON` e
296 `LOCATION`. Le 124 occorrenze di indirizzo sono ripetizioni nei messaggi,
non indirizzi unici: un valore ripreso dall'Agente deve essere riconosciuto
nuovamente perché una ripetizione non coperta lascerebbe il dato esposto.

## Limiti

- Il corpus dipende dagli scenari, dai cataloghi e dal modello generativo.
- La sovracampionatura degli indirizzi è intenzionale e non rappresenta la loro
  frequenza reale.
- Il gold è programmatico e riproducibile, ma non è stato approvato da più
  annotatori indipendenti.
- Le conversazioni sintetiche possono ripetere lessico e strutture più spesso
  del traffico reale.
- I risultati devono essere confermati in futuro su un gold umano e, con le
  necessarie autorizzazioni, su dati reali in ambiente controllato.

## Artefatti riproducibili

- Piano: `config/piano_dataset_paper_300.json`
- Configurazione di generazione: `config/generazione_paper_300.json`
- Prompt: `output/prompts_paper_300.jsonl`
- Conversazioni: `output/generazione_paper_300/conversazioni.jsonl`
- Dataset esportato: `output/dataset_detection_paper_300/`

