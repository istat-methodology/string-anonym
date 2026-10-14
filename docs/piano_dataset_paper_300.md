# Dataset sintetico per lo short paper: piano da 300 conversazioni

Stato al 14 ottobre 2026: implementazione completata; 300 prompt generati e
controllati localmente; chiamate al modello non ancora eseguite.

SHA-256 del file corrente `output/prompts_paper_300.jsonl`:
`7e87744eadb7156e9d36664e45fbd3aec63d847c5b84f15e25bd0a772a9bab70`.

## Obiettivo

Il corpus amplia la baseline senza cambiare il perimetro scientifico. Mantiene i
12 scenari già validati e aggiunge una sovracampionatura controllata degli
indirizzi. Il corpus resta sintetico e serve a valutare la pipeline, non a
stimare direttamente le prestazioni sul traffico reale.

## Disegno

Il piano versionato è `config/piano_dataset_paper_300.json`:

| Batch | Conversazioni | Funzione |
|---|---:|---|
| `general_core` | 230 | 10 esempi per ogni combinazione scenario–modalità disponibile |
| `general_extra` | 10 | riequilibrio di cinque scenari centrali, entrambe le modalità |
| `address_focus` | 60 | due scenari con ADDRESS obbligatorio, solo con dati personali |
| **Totale** | **300** | |

La distribuzione finale dei prompt è 175 conversazioni con dati personali e 125
senza. I due scenari address-oriented hanno 52 esempi ciascuno. Oltre ai 60 casi
mirati, il campionamento generale corrente contiene altri 13 prompt con ADDRESS:
73 schede complessive hanno quindi almeno un indirizzo previsto.

## Forme di indirizzo

Nel batch mirato ciascuna forma compare esattamente 10 volte:

| Variante | Esempio schematico | Componenti attese |
|---|---|---|
| `complete_standard` | `Via Angelo Lauri 96, Anzio` | tipo, strada, civico, comune |
| `without_street_type` | `Angelo Lauri 96, Anzio` | strada, civico, comune |
| `without_house_number` | `Via Angelo Lauri, Anzio` | tipo, strada, comune |
| `without_municipality` | `Via Angelo Lauri 96` | tipo, strada, civico |
| `complex_house_number` | `Via Angelo Lauri 96/A, Anzio` | tipo, strada, civico, estensione, comune |
| `with_internal` | `Via Angelo Lauri 96, interno 4, Anzio` | tipo, strada, civico, interno, comune |

I valori provengono dallo stradario e dal catalogo dei comuni locali. Civici,
estensioni e interni sono sintetici. Il prompt ordina di usare lo slot ADDRESS
come intera forma superficiale, senza aggiungere all'esterno “via”, “civico” o
altre parti che sfuggirebbero al gold.

## Contratto del gold

Ogni entità ADDRESS porta metadati strutturati con offset locali per:

- `street_type`, quando presente;
- `street_name`, sempre presente;
- `house_number`, quando presente;
- `house_extension`, per forme come `/A` o `bis`;
- `internal`, per interno o scala;
- `municipality`, quando presente.

Dopo la sostituzione dello slot, gli offset diventano assoluti nel messaggio.
L'esportatore `detection-5.2-address-components` conserva l'ADDRESS completo e
produce viste LOCATION annidate per la parte stradale e il comune, quando
presente. Per il corpus 5.1 precedente rimane disponibile il fallback basato su
“strada+civico, comune”.

Le componenti sono informazioni ausiliarie del gold: non diventano nuove classi
richieste ai modelli NER.

## Comandi

Rigenerazione deterministica dei prompt, soltanto se il file non esiste:

```sh
.venv/bin/python src/pipeline_generazione.py prepara --config config/generazione_paper_300.json
```

Controllo senza chiamate API:

```sh
.venv/bin/python src/pipeline_generazione.py controlla --config config/generazione_paper_300.json
```

Il controllo rifiuta prompt con seed o versione differenti e prompt i cui hash
non coincidono più con scenari, regole, piano e cataloghi locali correnti.

Generazione remota delle conversazioni:

```sh
.venv/bin/python src/pipeline_generazione.py genera --config config/generazione_paper_300.json
```

Il risultato sarà `output/generazione_paper_300/conversazioni.jsonl`. Il runner non
riprende automaticamente una generazione interrotta e non sovrascrive directory
esistenti. Dopo la generazione occorre esaminare gli stati `valido`,
`da_verificare` ed eventuali errori prima di congelare il corpus.

## Passaggi dopo la generazione

1. verificare completezza e stati delle 300 conversazioni;
2. correggere o rigenerare separatamente gli esiti non validi;
3. congelare il file finale e registrarne l'hash;
4. esportare il dataset con `src/esporta_dataset_detection.py --comuni`;
5. creare una nuova configurazione NER con percorso di output mai usato;
6. eseguire la run GPU e conservare manifest e revisioni dei modelli;
7. riportare prima exact-match `PERSON`–`LOCATION`;
8. eseguire poi `src/valuta_indirizzi.py` per ogni modello;
9. analizzare gli errori e chiudere le tabelle dello short paper.

Non ottimizzare soglie sullo stesso insieme usato come test. Se viene calibrata
la soglia di GLiNER, occorre separare e dichiarare un development set.
