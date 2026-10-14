# Query anonymization per le conversazioni Istat

Il progetto costruisce conversazioni sintetiche e valuta una pipeline di
riconoscimento degli elementi identificativi. L'obiettivo corrente è misurare
in modo riproducibile la **detection a livello di messaggio**, separandola dalle
decisioni contestuali di masking.

## Architettura

La pipeline è divisa in tre step:

1. **Detection del messaggio**: regex e NER leggono indipendentemente il testo
   originale; `merge_detection` conserva provenienza, overlap e disaccordi.
2. **Policy di conversazione**: userà l'intera chat per decidere se una detection
   debba essere mantenuta, mascherata o generalizzata. Non è nel workflow
   sperimentale corrente.
3. **Valutazione complessiva**: stimerà il rischio residuo della conversazione.
   Non è implementata. La valutazione a livello di intero dataset resta fuori
   dal perimetro corrente.

Il benchmark NER assegna ai modelli `PERSON` e `LOCATION`. Identificativi
strutturati come telefono, codice indagine, ruolo e numero pratica appartengono
al ramo regex o a lookup controllati. Le metriche end-to-end avranno senso dopo
la riconciliazione dei due rami.

## Baseline corrente

Il corpus di sviluppo comprende 46 conversazioni sintetiche. Il gold NER
multilivello contiene 35 span: 20 `PERSON` e 15 `LOCATION`. Per gli indirizzi
conserva sia l'intero `ADDRESS` nel gold canonico, sia strada+civico e comune
come `LOCATION` nella vista NER.

| Modello | Precision | Recall | F1 |
|---|---:|---:|---:|
| GLiNER multilingual | 28,2% | 82,9% | 42,0% |
| GLiNER multilingual PII | 20,3% | 82,9% | 32,6% |
| WikiNEuRal | 81,6% | 88,6% | 84,9% |
| Piiranha | 93,9% | 88,6% | 91,2% |

Sono risultati esplorativi su un campione piccolo, sintetico e usato durante lo
sviluppo. Non misurano la generalizzazione su chat reali. Gli indirizzi sono un
requisito operativo prioritario: oltre all'exact match, il prossimo esperimento
dovrà misurarne anche la copertura completa dei caratteri.

## Esecuzione

Controllo locale senza scaricare modelli:

```sh
.venv/bin/python src/confronta_modelli.py --solo-controllo
```

Esecuzione su GPU:

```sh
python src/confronta_modelli.py --device cuda:0
```

La configurazione predefinita è
`config/esperimento_ner_person_location_v5_multilivello.json`. Prima di una
nuova run occorre assegnare nel file una nuova cartella `output`, perché il
runner rifiuta le sovrascritture.

Test locali:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Struttura essenziale

- `config/`: scenari, regole, configurazione NER e piano del lotto paper;
- `data/`: cataloghi locali, inclusi i codici PSN reali;
- `src/`: generazione, esportazione, detection, merge e valutazione;
- `output/chat_v5_draft4_finale.jsonl`: corpus sintetico sorgente;
- `output/dataset_detection_v5_draft4_multilivello/`: input e gold corrente;
- `output/confronto_ner_person_location_v5_multilivello_run1/`: baseline salvata;
- `docs/`: decisioni, protocollo, risultati e istruzioni operative;
- `paper/`: materiale per la pubblicazione.

Gli esperimenti rimossi durante la pulizia restano recuperabili dalla cronologia
Git. Pesi dei modelli e credenziali non sono versionati.

## Documentazione

- [Pipeline operativa](docs/pipeline.md)
- [Decisione detection/policy](docs/decisione_architetturale_detection_policy.md)
- [Protocollo sperimentale](docs/protocollo_esperimento_detection_v5.md)
- [Risultati della baseline](docs/risultati_detection_v5_run1.md)
- [Valutazione operativa degli indirizzi](docs/valutazione_indirizzi.md)
- [Piano del dataset paper da 300 conversazioni](docs/piano_dataset_paper_300.md)
- [Confronto dei modelli](docs/confronto_modelli.md)
- [Setup Azure](docs/setup_azure.md)
- [Classificazione PSN](docs/classificazione_psn.md)
- [Regole regex](docs/baseline_regex.md)
