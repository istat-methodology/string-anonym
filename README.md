# Masking contestuale delle conversazioni Istat

Questo progetto studia come mascherare le informazioni identificative nelle
conversazioni del punto unico di contatto Istat, conservando il contenuto utile
alla richiesta statistica. Comprende la costruzione di un dataset sintetico
annotato e una pipeline di ricerca per confrontare regole e modelli.

## Il problema

Riconoscere un nome, un indirizzo o un codice non basta per decidere se
mascherarlo. Un indirizzo di residenza identifica l’utente; un territorio citato
per richiedere dati statistici deve invece rimanere leggibile. Anche i riferimenti
pubblici alle indagini vanno distinti dalle credenziali e dai numeri di pratica.
Le informazioni possono emergere in più turni ed essere ripetute dal chatbot.

Il compito è individuare le porzioni di testo da mascherare, valutarne i confini
e preservare il resto della conversazione. Il masking di queste porzioni non
costituisce, da solo, una garanzia di anonimizzazione complessiva.

## Approccio di ricerca

La generazione sintetica separa la costruzione del dialogo dall’inserimento dei
valori identificativi. Il modello genera conversazioni con slot; il codice
inserisce i valori campionati localmente e costruisce le annotazioni con posizioni
esatte. Questo rende tracciabile il riferimento atteso, ma non sostituisce la
revisione dei contenuti o la ricerca di dati introdotti fuori dagli slot.

Per il masking proponiamo due canali complementari: regex per forme
riconoscibili e un modello contestuale per le espressioni variabili e la loro
funzione nel dialogo. Il modello potrà riconoscere entità anche senza una
corrispondenza regex. Il confronto fra regole, modello e sistema ibrido dovrà
misurarne il contributo, senza presumere che la combinazione sia sempre migliore.

## Stato attuale

- Generazione e validazione di conversazioni sintetiche, con provenienza e versioni.
- Esportazione separata di input, annotazioni attese e informazioni di revisione.
- Baseline regex e valutatore indipendente dal modello, entrambi locali.
- Runner configurabile per confrontare quattro modelli NER (da verificare sulla GPU).
- Sette categorie: PERSON, ADDRESS, EMAIL, PHONE, COD_UTENTE, PASSWORD, NUM_PRATICA.

Il confronto sperimentale, il fine-tuning e la sostituzione coerente delle predizioni
lungo la conversazione sono ancora da implementare. I lotti esistenti sono
materiale di sviluppo: non costituiscono un test finale indipendente.

La prima baseline, su 24 conversazioni sintetiche con 46 occorrenze attese nei
dialoghi, riconosce 27 span esatti, con 19 omissioni e nessun falso positivo nel
campione: precisione 100%, recall 58,7%, F1 74,0%. Nomi e indirizzi non sono coperti
dalle regole attuali. Sono risultati preliminari rispetto ad annotazioni non
ancora approvate come gold, non una stima delle prestazioni sul traffico reale.

## Documentazione

| Documento | Scopo |
|---|---|
| [Metodologia del masking](docs/metodologia_masking.md) | Obiettivi, workflow, disegno sperimentale, dati e metriche |
| [Pipeline operativa](docs/pipeline.md) | Comandi, input/output, verifiche e istruzioni di generazione |
| [Convenzioni di masking](docs/casi_ambigui_masking.md) | Decisioni sui casi ambigui e riferimenti da conservare |
| [Specifica della generazione](specifica_pipeline_conversazioni_sintetiche.md) | Requisiti della pipeline sintetica |
| [Baseline regex](docs/baseline_regex.md) | Regole implementate e limiti |
| [Confronto modelli](docs/confronto_modelli.md) | Configurazione, esecuzione sequenziale e limiti del confronto |
| [Valutatore](docs/valutatore_masking.md) | Formati delle predizioni e interpretazione dei risultati |

## Organizzazione

`src/` contiene il codice, `config/` le configurazioni, `tests/` le verifiche,
`data/` le sorgenti locali e `docs/` la documentazione. `src/original/` conserva
il prototipo storico. `output/` contiene dataset sintetici e risultati degli esperimenti, versionati
in Git per trasferirli anche sulla VM Azure. I pesi dei modelli restano nella
cache di Hugging Face, fuori dal repository. Le credenziali restano in `.env`,
non versionato; `.env.example` documenta la configurazione.

Il lavoro procede per step verificabili. L’esecuzione delle generazioni e degli
esperimenti resta a cura dell’utente. La ricerca utilizzerà modelli a pesi aperti;
l’obiettivo successivo è verificarne l’esecuzione sull’infrastruttura Istat.
