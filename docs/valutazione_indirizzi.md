# Valutazione operativa degli indirizzi

## Ruolo nel protocollo

La valutazione degli indirizzi è un'analisi **successiva e complementare** alle
metriche NER standard. Non modifica il gold `PERSON`–`LOCATION`, le predizioni o
l'exact-match F1. Risponde a una domanda diversa: quanta parte identificativa di
un indirizzo rimarrebbe visibile dopo aver mascherato gli span `LOCATION`
predetti?

Nel corpus 5.2 il gold canonico rappresenta l'intero `ADDRESS` e conserva
componenti strutturate opzionali: tipo di strada, denominazione, civico,
estensione del civico, interno o scala e comune. Il valutatore le aggrega nelle
viste strada, civico, interno e comune, senza chiedere ai modelli nuove etichette.
Per la baseline 5.1 resta disponibile il fallback su `street_civic` e
`municipality`.

## Metriche

`src/valuta_indirizzi.py` calcola:

- copertura dei caratteri alfanumerici dell'indirizzo completo;
- tasso di indirizzi completamente coperti;
- tasso di esposizione residua;
- copertura e completezza separate di strada, civico, interno e comune;
- distribuzione degli esiti operativi;
- dettaglio per indirizzo, incluso il testo alfanumerico rimasto visibile.

Spazi e punteggiatura non sono conteggiati come informazione residua. Un
indirizzo è “completo” solo se tutti i caratteri alfanumerici di strada, civico
e comune sono coperti dall'unione delle predizioni `LOCATION` sul messaggio.

Gli esiti sono:

| Esito | Interpretazione |
|---|---|
| `complete` | strada, civico e comune completamente coperti |
| `house_number_exposed` | strada e comune coperti, civico esposto |
| `municipality_exposed` | strada e civico coperti, comune esposto |
| `municipality_only` | coperto soltanto il comune |
| `uncovered` | nessun carattere significativo coperto |
| `partial_other` | qualsiasi altra copertura parziale |

La tassonomia è descrittiva, non una scala normativa di rischio. In particolare,
un confine come “Angelo Lauri 96” riceve un'elevata copertura dei caratteri, ma
non diventa un indirizzo completamente protetto perché “Via” resta visibile.

## Esecuzione

Il comando va ripetuto per ciascun modello:

```sh
.venv/bin/python src/valuta_indirizzi.py \
  --input output/dataset_detection_v5_draft4_multilivello/input.jsonl \
  --gold output/dataset_detection_v5_draft4_multilivello/detections_attese.jsonl \
  --predictions output/confronto_ner_person_location_v5_multilivello_run1/MODELLO/predizioni.jsonl \
  --output output/confronto_ner_person_location_v5_multilivello_run1/MODELLO/valutazione_indirizzi.json
```

Il report registra gli hash delle tre fonti e rifiuta sovrascritture.

## Controllo sulla baseline corrente

Il corpus contiene soltanto due indirizzi; i risultati seguenti servono quindi a
verificare il metodo, non a stimare prestazioni stabili.

| Modello | Indirizzi completi | Copertura caratteri | Esito sui due casi |
|---|---:|---:|---|
| GLiNER multilingual | 2/2 | 100,0% | `complete` |
| GLiNER multilingual PII | 0/2 | 0,0% | `uncovered` |
| WikiNEuRal | 0/2 | 90,5% | `house_number_exposed` |
| Piiranha | 0/2 | 28,6% | `municipality_only` |

Questa vista cambia l'interpretazione della baseline. GLiNER multilingual ha
molti falsi positivi nella metrica NER generale, ma copre integralmente entrambi
gli indirizzi. WikiNEuRal protegge strada e comune ma lascia visibile il civico.
Piiranha riconosce il comune, ma non la parte stradale nella configurazione
corrente. Il dataset ampio dovrà includere molte più forme di indirizzo prima di
trarre conclusioni comparative.

## Limiti ed estensioni

La versione 1.0 gestisce le sei forme previste dal piano paper, incluse assenza
di designatore, civico o comune, civici complessi e interno/scala. Non tratta
ancora CAP, frazioni, edifici, indirizzi multipli nello stesso span o forme
libere non prodotte dal generatore. Questi casi costituiscono una naturale
estensione per il paper successivo e per la pipeline di prodotto.
