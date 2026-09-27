# Documentazione storica fino alla versione 3.1

I comandi e i formati seguenti descrivono la versione precedente.
Per la versione corrente usare il README nella radice.

# Conversazioni sintetiche Istat

## Generazione locale dei prompt

Richiede Python 3.10 o successivo, senza librerie aggiuntive. Non chiama API,
non carica conversazioni reali e non modifica i sorgenti originali di Samantha.

```sh
python3 src/genera_prompt.py --output output/prompts.jsonl
```

Il comando prepara 24 prompt: 6 scenari × 2 modalità × 2 esempi.
Ogni riga JSONL contiene una scheda e i messaggi di istruzione da passare
successivamente al modello. Non è ancora un dataset di dialoghi generati né
un file pronto per l'API Batch: l'invocazione dell'endpoint è una fase successiva.

```sh
python3 src/genera_prompt.py --scenario recupero_accesso --per-modalita 3 --seed 7 --data-inizio 2026-04-01 --giorni 21 --output output/accesso.jsonl
```

L'output esistente non viene sovrascritto. Il seed controlla esclusivamente le
scelte locali; non promette determinismo del futuro modello generativo.

## Scenari e formato

`config/scenari.json` contiene i tre scenari iniziali e i tre scenari aggiunti nella versione 3.0.
Le indicazioni operative sono tracce di simulazione da validare, non documentazione
ufficiale del servizio. Nuovi scenari e sezioni possono essere aggiunti al catalogo.
La chiave indagine è una stringa (mantiene gli zeri iniziali), oppure null quando
non pertinente. Sezione e scenario guidano la generazione e restano nella scheda.

Metadati richiesti nel dialogo: `canale`, `data_sintetica`, `chiave_indagine`,
`descrizione`. Nessuna classificazione del revisore, valutazione o soddisfazione.
Seguono `conversazione` e `trattamento_atteso`.

Modalità:
- `senza_dati_personali`: nessuna entità da mascherare;
- `con_dati_personali`: entità personali inserite nel dialogo;

In entrambe le modalità i riferimenti utili al servizio vanno conservati.
Con dati personali si campiona un sottoinsieme non vuoto delle entità ammesse
nello scenario: il numero di entità è uniforme tra 1 e la dimensione della lista,
poi si estrae senza ripetizioni. Il seed controlla anche questa scelta.
La distribuzione uniforme delle modalità è per il pilota e non stima la
frequenza delle richieste reali.

I segnaposto `{{persona_1}}`, `{{email_1}}`, `{{indirizzo_1}}` permetteranno una
successiva sostituzione locale con valori sintetici, utilizzando le liste in
`data/`. Il parser legge ora tutti e quattro i dataset. Ogni entità del prompt include un
`valore_proposto`; il modello continuerà a scrivere segnaposto, da sostituire
localmente nella fase successiva.
Le annotazioni generate dal modello dovranno essere verificate: un formato
richiesto nel prompt non garantisce correttezza sintattica o semantica.

Per documentare l'esperimento sono conservati versione del prompt, versione del
catalogo, seed, scheda e istruzioni complete. Modello e parametri API saranno
registrati dalla futura fase di generazione delle risposte.

## Lettura dei dati e sampling

`src/parse_input.py` prepara nomi e cognomi unici, una mappa codice ISTAT →
comune e le coppie uniche (codice ISTAT, odonimo). Legge gli indirizzi riga per
riga: i civici originali non vengono conservati. Le strade omonime nello stesso
comune vengono accorpate anche se riferite a località o codici strada diversi:
questa è una lista lessicale per generare esempi, non un archivio geografico.
Si usa ODONIMO; le dizioni linguistiche alternative non sono incluse.

```sh
python3 src/parse_input.py --output-strade data/strade_lazio.csv
python3 src/genera_prompt.py --output output/prompts_con_entita.jsonl
```

Il CSV compatto è facoltativo; il generatore legge i quattro originali a ogni
esecuzione. `--data-dir` permette di specificarne la cartella. Nessun originale
viene modificato. Il parser stampa i conteggi e segnala codici comune sconosciuti.

Il sampling è uniforme sulle liste ordinate e sulle coppie comune-strada uniche,
non sulle frequenze demografiche. Il civico è estratto tra 1 e 300 e non ne viene
verificata l'esistenza. Le email sintetiche derivano dal nome campionato e usano
example.org. Nomi e cognomi sono combinati indipendentemente: non rappresentano
identità reali verificate. Liste e seed uguali producono le stesse scelte locali.

## Generazione delle conversazioni su Azure Foundry

Lo script `src/genera_chat.py` legge i prompt già preparati ed effettua una
chiamata Responses per conversazione. Usa `API_KEY` dal `.env` nella radice
(o `AZURE_OPENAI_API_KEY`); non serve `azure.identity`. Il `.env` è escluso da Git.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/genera_chat.py --limit 1 --output output/chat_prova.jsonl
```

Per scegliere un prompt con entità, oppure elaborare tutti i 12 prompt:

```sh
.venv/bin/python src/genera_chat.py --id recupero_accesso-con_dati_personali-0001 --output output/chat_accesso.jsonl
.venv/bin/python src/genera_chat.py --limit 12 --output output/chat_lotto.jsonl
```

Default: endpoint `https://foundry-ateco.services.ai.azure.com/openai/v1/`,
deployment `gpt-5.6-terra`. Sono modificabili con `--endpoint` e `--deployment`,
oppure con `AZURE_OPENAI_ENDPOINT` e `AZURE_OPENAI_DEPLOYMENT` nel `.env`.
Il nome del deployment viene passato esattamente al parametro `model`.

Ogni riga dell'output conserva prompt, data di esecuzione, deployment, risposta
originale (inclusi modello restituito e consumo token), stato dei controlli,
`chat_template` con segnaposto e `chat` con i valori campionati inseriti localmente.
Il trattamento atteso mantiene i segnaposto, associabili ai valori nella scheda.
Non vengono inviati file di conversazioni reali: solo il prompt sintetico scelto.

Si richiede JSON e si controllano metadati, ruoli, numero di scambi, segnaposto
ed entità annotate. `valido` significa che questi controlli sono superati, non
che il dialogo sia stato revisionato semanticamente o che ogni eventuale dato
personale inventato sia stato individuato. Risposte incomplete o non conformi
restano salvate come `da_verificare`, senza essere considerate esempi validi.

Non si sovrascrive un output esistente. Ogni risultato viene salvato subito;
un errore API interrompe il lotto. Nessun retry automatico: in caso di timeout
la richiesta potrebbe essere stata elaborata dal servizio. Il limite predefinito
è una conversazione e 6000 token di output (`--max-output-tokens`); non viene
imposta una temperatura, per rispettare i parametri supportati dal deployment.

Test locali (senza API):

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Riferimento: [API Azure OpenAI v1](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle).

## Recupero locale e versione 2

```sh
.venv/bin/python src/rivalida_chat.py --input output/chat_lotto.jsonl --output output/chat_lotto_recuperato.jsonl
```

Non usa la rete né la chiave. Conserva la risposta originale e l'esito precedente.
Normalizza `text` in `testo` solo se `testo` è assente; due campi contemporanei
restano un errore. Il numero di scambi è indicativo: lo scostamento viene registrato
in `validazione.avvisi`, mentre le rinomine sono in `validazione.correzioni`.
Conversazioni vuote, coppie incomplete, ruoli errati, metadati alterati ed errori
nelle entità restano bloccanti. `valido` indica solo validazione strutturale.

Il lotto recuperato conserva le modalità storiche (incluso `misto`) e i prompt
originali: non viene riclassificato retroattivamente. Il nuovo lotto locale
`output/prompts_v2.jsonl` contiene 12 prompt con due modalità ed entità variabili.
È ora l'input predefinito di `genera_chat.py`; i vecchi file restano disponibili
con `--input`. Per rigenerare i prompt scegliere un nuovo percorso, quindi passarlo
al generatore di chat. In questo aggiornamento non sono state effettuate chiamate API.

## Lotto v3: sei scenari

Il catalogo 3.0 aggiunge comunicazione intestata a un precedente referente,
cambio di residenza e ricerca di dati territoriali. I nuovi casi non impongono
un'indagine specifica: nome e chiave sono null. Nella ricerca territoriale il
comune è campionato dall'elenco dei comuni e l'anno tra 2022, 2023 e 2024:
sono riferimenti da conservare, separati dalle entità personali.

Il prompt 3.0 chiede di concludere naturalmente, senza turni di riempimento,
e concretizza lo stile con refusi senza alterare segnaposto e codici.
I 24 prompt sono bilanciati: 6 scenari × 2 modalità × 2 esempi. Gli output
precedenti sono conservati. Per selezionare esplicitamente questo nuovo lotto:

```sh
.venv/bin/python src/genera_chat.py --input output/prompts_v3.jsonl --limit 24 --output output/chat_lotto_v3.jsonl
```

Il default del generatore di chat resta il lotto v2: specificare `--input`
per il v3. Questo lotto contiene prompt, non nuove risposte del modello;
naturalità e rispetto dello stile vanno verificati dopo l'esecuzione.

## Versione 3.1

La conversazione può terminare con un messaggio dell'utente dopo almeno una
risposta del chatbot. Restano obbligatori messaggi non vuoti e ruoli alternati.
La validazione 2.1 registra coppie complete (`scambi_effettivi`), numero totale
di messaggi e presenza di una chiusura dell'utente; non certifica il significato
dell'ultima frase.

Per `comunicazione_altra_persona`, `email_indipendente: true` genera un recapito
`contatto.<numero>@example.org` per il nuovo contatto, senza derivarlo dal nome
del precedente referente. Gli altri scenari conservano l'associazione nome-email.

Il lotto `chat_lotto_v3_recuperato.jsonl` è solo rivalidato: 23 esempi superano
la struttura, uno rimane da verificare per un messaggio vuoto. Le identità del
vecchio lotto non sono state riscritte: l'incoerenza semantica del recapito nel
cambio referente resta da considerare nella revisione. Il fix del campionamento
si applica ai nuovi prompt `output/prompts_v3_1.jsonl` (24 prompt).

```sh
.venv/bin/python src/genera_chat.py --input output/prompts_v3_1.jsonl --limit 24 --output output/chat_lotto_v3_1.jsonl
```

## Validazione 2.2 e recupero mirato

Un messaggio vuoto interno può essere rimosso solo quando è seguito da un
messaggio non vuoto dello stesso ruolo; dopo la rimozione vengono riapplicati
tutti i controlli. Vuoti finali e risposte mancanti restano bloccanti.
Ogni rimozione è registrata; la risposta originale non viene alterata.

Un controllo lessicale segnala inoltre gli stati `in compilazione`, `in bozza`
e `in sola lettura` presenti nella descrizione o nell'elenco da conservare,
ma assenti dai messaggi utente. Una domanda del chatbot che elenca possibili
stati non vale come conferma. I casi sono `da_verificare`: è un segnale limitato,
può non riconoscere parafrasi o negazioni e non certifica la coerenza semantica
generale. Non aggiunge informazioni né modifica il dialogo per farlo passare.
