# Protocollo preliminare dell'esperimento detection 5.0

## Obiettivo e perimetro

L'esperimento confronta modelli NER sul primo step della pipeline: riconoscere
span e categorie in ciascun messaggio, senza applicare decisioni di policy. Ogni
messaggio è elaborato indipendentemente; la conversazione è soltanto il contenitore
del dataset. Non si misurano masking finale, rischio residuo o anonimizzazione.

La domanda sperimentale primaria è: quanto bene modelli generalisti e modelli
orientati alle PII riconoscono `PERSON` e `LOCATION` nelle conversazioni
istituzionali sintetiche, a parità di input e senza fine-tuning? Le altre
categorie appartengono principalmente al ramo regex e non devono abbassare la
misura del componente NER.

## Corpus e riferimento atteso

Il corpus `chat_v5_draft4_finale.jsonl` contiene 46 conversazioni sintetiche.
L'esportatore multilivello produce 46 input e 206 detection canoniche. La vista
NER usata nel confronto contiene 35 span: 20 `PERSON` e 15 `LOCATION`.
Le categorie presenti nel gold canonico sono tredici:

| Categoria | Occorrenze |
|---|---:|
| ADDRESS | 2 |
| COD_INDAGINE | 37 |
| COD_UTENTE | 10 |
| DATE | 10 |
| EMAIL | 19 |
| INDAGINE | 37 |
| LOCATION | 15 |
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

La baseline corrente confronta GLiNER multilingual, GLiNER multilingual PII,
WikiNEuRal e Piiranha. I modelli sono eseguiti in sequenza sullo stesso hardware.
Gli output nativi, le conversioni di categoria, le revisioni dei pesi, i tempi e
la memoria GPU sono conservati. La soglia iniziale di GLiNER è 0,5; non viene
ottimizzata sul corpus prima del primo run.

Tutti i modelli sono interrogati o mappati soltanto su `PERSON` e `LOCATION`.

L'assegnazione metodologica corrente è:

| Componente | Categorie di responsabilità primaria |
|---|---|
| NER | `PERSON`, `LOCATION` |
| Regex o lookup controllato | `PHONE`, `COD_INDAGINE`, `INDAGINE`, `ROLE`, `NUM_PRATICA` e altri identificativi strutturati |
| `merge_detection` | unione delle detection coincidenti e conservazione esplicita di conflitti e sovrapposizioni |

La copertura regex delle categorie dichiarate deve essere implementata e
verificata: l'assegnazione non equivale ancora a una prestazione del 100%.

## Metriche e analisi

La misura primaria del NER è F1 micro su `PERSON` e `LOCATION`, con
corrispondenza esatta di confini e categoria. Si riportano anche precisione e
recall, risultati per categoria e ruolo,
copertura dei caratteri attesi, falsi positivi nelle conversazioni negative,
fallimenti tecnici, tempi e picchi di memoria. Gli errori saranno ispezionati per
distinguere confini errati, tipo errato e omissione.

La metrica globale su tutte le categorie resta una diagnostica secondaria della
run solo NER. Diventerà una metrica end-to-end soltanto quando le predizioni NER
saranno unite alle predizioni regex e valutate dopo `merge_detection`.

### Gold multilivello degli indirizzi

La run pilota ha mostrato un limite dell'adattatore legacy: un indirizzo completo
era annotato soltanto come `ADDRESS`, rendendo falsi positivi la strada e il
comune correttamente estratti come `LOCATION`. Dalla versione
`detection-5.1-multilivello` vale una regola definita indipendentemente dai
modelli:

- l'intero indirizzo resta `ADDRESS`;
- strada e civico sono anche `LOCATION`;
- il comune è anche `LOCATION`;
- le detection canoniche possono essere annidate e sovrapposte.

La scomposizione avviene soltanto quando il suffisso dell'indirizzo coincide con
un comune del catalogo locale. `annotazioni_ner_attese.jsonl` espone la vista
`PERSON`–`LOCATION`; il gold canonico conserva anche `ADDRESS`. Il dataset e le
run precedenti restano immutati per documentare l'evoluzione metodologica.

Non è previsto un test di significatività nel primo run: il campione è piccolo,
sintetico e fortemente sbilanciato. Le categorie con una o due occorrenze vanno
descritte come casi esplorativi, non confrontate mediante percentuali stabili.

## Riproduzione

Controllo locale, senza download:

```sh
.venv/bin/python src/confronta_modelli.py \
  --config config/esperimento_ner_person_location_v5_multilivello.json \
  --solo-controllo
```

Esecuzione sulla GPU:

```sh
python src/confronta_modelli.py \
  --config config/esperimento_ner_person_location_v5_multilivello.json \
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
