# Pipeline operativa corrente

Tutti i comandi vanno eseguiti dalla root della repository. Gli script rifiutano
di sovrascrivere gli output esistenti.

## 1. Generazione delle conversazioni

Gli scenari sono in `config/scenari.json`; i valori strutturati e i codici PSN
sono campionati localmente. Il modello genera la conversazione usando gli slot,
mentre il codice inserisce i valori e costruisce gli offset. Detection e policy
non sono affidate al prompt di generazione.

Il corpus congelato della baseline è:

```text
output/chat_v5_draft4_finale.jsonl
```

Per preparare un lotto più grande si usano `src/genera_prompt.py`,
`src/genera_lotto.py` e `src/genera_chat.py`. Il nuovo lotto deve avere un nome
e un output distinti dalla baseline; prompt, modello, seed e configurazione
devono essere conservati per la riproducibilità.

## 2. Esportazione del gold multilivello

```sh
.venv/bin/python src/esporta_dataset_detection.py \
  --input output/chat_v5_draft4_finale.jsonl \
  --output output/dataset_detection_v5_draft4_multilivello \
  --comuni data/codici_comuni.csv
```

L'output contiene:

- `input.jsonl`: ID, ruoli e testi, senza gold;
- `detections_attese.jsonl`: gold canonico, che ammette overlap;
- `annotazioni_ner_attese.jsonl`: vista valutabile `PERSON`–`LOCATION`;
- `annotazioni_attese.jsonl`: adattatore piatto del valutatore;
- `provenienza.jsonl`, `esclusi.jsonl` e `manifest.json`: tracciabilità.

Il corpus corrente contiene 46 conversazioni, 206 detection canoniche e 35
annotazioni NER: 20 `PERSON` e 15 `LOCATION`. Negli indirizzi, strada+civico e
comune sono entità `LOCATION` distinte; l'intero indirizzo resta anche
`ADDRESS` nel gold canonico.

## 3. Controllo e run NER

Controllo offline:

```sh
.venv/bin/python src/confronta_modelli.py --solo-controllo
```

Run su GPU:

```sh
python src/confronta_modelli.py --device cuda:0
```

Entrambi usano per default
`config/esperimento_ner_person_location_v5_multilivello.json`. Per una nuova
esecuzione modificare prima il campo `output` della configurazione. Il runner
salva configurazione, revisioni risolte, hash degli input, output nativi,
predizioni normalizzate, metriche, tempi e picchi di memoria.

## 4. Interpretazione

La metrica primaria è l'exact-match micro F1 su `PERSON` e `LOCATION`. Vanno
sempre riportati anche precision, recall, numero di conversazioni valutate e
fallimenti tecnici. Il campione è sintetico e di sviluppo: non è un test
indipendente sul traffico reale.

Per gli indirizzi l'exact match non basta a descrivere il rischio operativo. Il
prossimo benchmark deve aggiungere una misura di copertura dei caratteri
dell'indirizzo e un'analisi esplicita dei frammenti lasciati visibili.

## 5. Sviluppi successivi

1. generare e congelare un corpus sintetico più grande;
2. verificare il ramo regex sugli identificativi strutturati;
3. unire regex e NER tramite `merge_detection` e misurare la pipeline completa;
4. sperimentare separatamente la policy a livello di conversazione;
5. rinviare la valutazione complessiva del rischio residuo a un lavoro futuro.

La policy di conversazione e la valutazione complessiva non fanno parte degli
output conservati nella baseline corrente.
