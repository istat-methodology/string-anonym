# Conversazioni sintetiche Istat

Pipeline locale per preparare prompt, generare una conversazione per chiamata e
annotare le occorrenze delle entità. Riferimento:
[specifica 0.4](specifica_pipeline_conversazioni_sintetiche.md).

## Stato dell’incremento 4.0

- Cinque input locali; unico stradario letto: `data/strade_lazio.csv`.
- Catalogo PSN con tipo di rispondente e fonte della classificazione.
- Sei casi pilota collegati agli ID della specifica; associazioni PSN esplicite.
- Nuovi metadati senza `canale`; chiave portale a null, separata dal codice PSN.
- Etichette attive: PERSON, EMAIL, ADDRESS, COD_UTENTE, PASSWORD, NUM_PRATICA, PHONE.
- Span esatti per messaggi utente, chatbot, descrizione ed eventuali ripetizioni
  nelle spiegazioni del trattamento. La risposta originale resta conservata.
- I lotti storici restano rivalidabili con il loro formato originale.

Questo incremento non completa la specifica: restano i generatori CF, PIVA e ORG,
il formato COD_UNITA da concordare, l’estensione progressiva ai 55 scenari,
le quote linguistiche e gli split di training/development/test, la ripresa dei
lotti e una revisione semantica più ampia. Lo split dei nuovi prompt è `pilota`.

## Modificare le regole

| File | Contenuto modificabile |
|---|---|
| `config/regole_generazione.json` | Prefissi e lunghezze dei codici utente, formato delle pratiche, password e telefoni. |
| `config/scenari.json` | Situazioni, entità ammesse, indagini compatibili, istruzioni generiche di risposta. |
| `data/codici_psn.csv` | Coppie codice–nome, classificazione e fonti. |

Il formato pratica è provvisorio: cifre + `/` + anno a due cifre. `Prot.n.` resta
fuori dal valore e dallo span. COD_UNITA è dichiarato in attesa di formato:
il generatore restituisce un errore se gli viene richiesto.
Le regole JSON sono salvate anche nel lotto dei prompt. I valori sono sintetici;
non rappresentano credenziali effettive né recapiti verificati.

## Preparare i prompt senza API

Richiede Python 3.10+, senza dipendenze esterne:

```sh
python3 src/parse_input.py
python3 src/genera_prompt.py --seed 0 --output output/prompts_v4.jsonl
python3 -m unittest discover -s tests -v
```

Il lotto locale `output/prompts_v4.jsonl` è già preparato con seed 0, scelto per
includere tutte e sette le etichette attive. Per ricrearlo scegliere un nuovo
percorso di output. Non contiene risposte del modello.

Il default prepara 24 prompt: sei casi × due modalità × due esempi. I codici
PSN sono campionati come coppie codice–nome dalla lista ammessa per lo scenario;
le categorie `da_verificare` non vengono selezionate. Non si deducono chiavi
di portale, obblighi, scadenze o procedure dai cataloghi.

Per cambiare regole o selezionare un caso:

```sh
python3 src/genera_prompt.py --scenario recupero_accesso --regole config/regole_generazione.json --seed 7 --per-modalita 3 --output output/accesso_v4.jsonl
```

Nessun output esistente viene sovrascritto. I prompt conservano seed, versioni,
regole, istruzioni e impronte SHA-256 dei cinque input e dei file di configurazione.
Il seed riproduce le scelte locali a parità di input e codice; non garantisce
risposte identiche del modello. Gli ID sono ancora locali al lotto.

## Generare e rivalidare le conversazioni

La generazione usa le dipendenze di `requirements.txt` e il client già previsto
per Azure Foundry. Il percorso dei prompt è obbligatorio, per evitare di usare
inavvertitamente un lotto storico:

```sh
.venv/bin/python src/genera_chat.py --input output/prompts_v4.jsonl --max-conversazioni 1 --output output/chat_v4_prova.jsonl
python3 src/rivalida_chat.py --input output/chat_v4_prova.jsonl --output output/chat_v4_rivalidate.jsonl
```

`--limit` rimane un alias di `--max-conversazioni`. Le credenziali restano nel
`.env` escluso da Git (`API_KEY` o `AZURE_OPENAI_API_KEY`); non vengono salvate
negli output. Endpoint e deployment sono configurabili come in precedenza.
La rivalidazione locale non richiede client API né credenziali.

Ogni risposta viene salvata progressivamente. Gli errori API interrompono il
lotto; non sono introdotti retry o ripresa automatica. `valido` significa che
sono superati i controlli implementati, non una revisione semantica completa:
identificativi inventati fuori dagli slot e riepiloghi infedeli richiedono ancora
revisione. I controlli lessicali esistenti coprono solo alcuni stati del questionario.

## Annotazioni

Nel nuovo formato `chat.trattamento_atteso.mascherare` contiene un oggetto per
ogni occorrenza con `campo`, `start`, `end`, `tipo`, `id_entita`, `id_forma`,
`testo` e `sostituzione`. `campo` identifica il singolo testo, per esempio
`conversazione.0.testo` o `metadati.descrizione`. L’indice messaggio parte da zero.
Gli offset sono caratteri Unicode secondo Python, start incluso ed end escluso.
Vale sempre `testo_del_campo[start:end] == annotazione["testo"]`.

Il template mantiene gli slot e l’elenco proposto dal modello; gli span della
chat finale sono costruiti localmente, senza ricerche di sottostringhe.
Il sostitutore supporta forme esplicite collegate allo stesso `id_entita`;
il pilota campiona per ora una forma completa per entità.

## Documentazione e revisione

- [Classificazione PSN e limiti](docs/classificazione_psn.md).
- [Convenzioni di mascheramento concordate e punti aperti](docs/casi_ambigui_masking.md).
- [Documentazione storica fino alla versione 3.1](docs/cronologia_pipeline_v3.md).
