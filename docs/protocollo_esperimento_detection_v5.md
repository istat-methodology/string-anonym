# Protocollo preliminare dell'esperimento detection 5.0

## Obiettivo e perimetro

L'esperimento confronta modelli NER sul primo step della pipeline: riconoscere
span e categorie in ciascun messaggio, senza applicare decisioni di policy. Ogni
messaggio è elaborato indipendentemente; la conversazione è soltanto il contenitore
del dataset. Non si misurano masking finale, rischio residuo o anonimizzazione.

La domanda sperimentale preliminare è: quanto bene modelli generalisti e modelli
orientati alle PII riconoscono le categorie richieste dalle conversazioni
istituzionali sintetiche, a parità di input e senza fine-tuning?

## Corpus e riferimento atteso

Il corpus `chat_v5_draft4_finale.jsonl` contiene 46 conversazioni sintetiche. Il
nuovo esportatore produce 46 input, 202 detection attese e 6 conversazioni senza
detection. Le categorie presenti sono tredici:

| Categoria | Occorrenze |
|---|---:|
| ADDRESS | 2 |
| COD_INDAGINE | 37 |
| COD_UTENTE | 10 |
| DATE | 10 |
| EMAIL | 19 |
| INDAGINE | 37 |
| LOCATION | 11 |
| NUM_PRATICA | 11 |
| ORGANIZATION | 26 |
| PASSWORD | 1 |
| PERSON | 20 |
| PHONE | 2 |
| ROLE | 16 |

Le detection derivano dagli slot sintetici e dai riferimenti controllati: sono un
riferimento di sviluppo riproducibile, non un gold standard umano. Lo stesso
corpus è stato usato per progettare e verificare la pipeline; i risultati non
sono quindi una stima indipendente della generalizzazione sul traffico reale.

## Separazione dei dati

`src/esporta_dataset_detection.py` valida testi e offset e produce file separati:

- `input.jsonl`: soltanto ID tecnico, ruoli e testi;
- `detections_attese.jsonl`: formato canonico, con fonti delle detection;
- `annotazioni_attese.jsonl`: adattatore per il valutatore corrente;
- `provenienza.jsonl`, `esclusi.jsonl` e `manifest.json`: tracciabilità.

Prompt, ipotesi di policy, decisioni attese e metadati descrittivi non entrano
nell'input dei modelli. Gli ID incorporano l'hash SHA-256 della fonte, ma non
sono passati come testo al modello.

## Modelli e procedura

La prima esecuzione confronta GLiNER multilingual, GLiNER multilingual PII,
WikiNEuRal e Piiranha. I modelli sono eseguiti in sequenza sullo stesso hardware.
Gli output nativi, le conversioni di categoria, le revisioni dei pesi, i tempi e
la memoria GPU sono conservati. La soglia iniziale di GLiNER è 0,5; non viene
ottimizzata sul corpus prima del primo run.

WikiNEuRal e Piiranha non coprono l'intero schema. I loro risultati globali
misurano quindi anche la copertura dello schema, non soltanto la qualità entro le
categorie native. Le metriche per categoria sono necessarie per interpretarli.

## Metriche e analisi

La misura primaria è F1 micro su corrispondenza esatta di confini e categoria.
Si riportano anche precisione e recall, risultati per categoria e ruolo,
copertura dei caratteri attesi, falsi positivi nelle conversazioni negative,
fallimenti tecnici, tempi e picchi di memoria. Gli errori saranno ispezionati per
distinguere confini errati, tipo errato e omissione.

Non è previsto un test di significatività nel primo run: il campione è piccolo,
sintetico e fortemente sbilanciato. Le categorie con una o due occorrenze vanno
descritte come casi esplorativi, non confrontate mediante percentuali stabili.

## Riproduzione

Controllo locale, senza download:

```sh
.venv/bin/python src/confronta_modelli.py \
  --config config/esperimento_detection_v5.json \
  --solo-controllo
```

Esecuzione sulla GPU:

```sh
python src/confronta_modelli.py \
  --config config/esperimento_detection_v5.json \
  --device cuda:0
```

Il percorso di output deve essere nuovo a ogni run. Prima di usare i risultati
nello short paper occorre registrare ambiente CUDA, modello della GPU, revisioni
risolte dei pesi e commit Git del progetto.

## Passi successivi

Dopo il primo run: analisi degli errori, eventuale secondo run motivato e congelato,
integrazione con regex tramite `merge_detection`, quindi applicazione separata
della policy a livello di conversazione. La valutazione complessiva del rischio
residuo della conversazione rimane futura; quella sull'intero dataset resta fuori
dal perimetro corrente.
