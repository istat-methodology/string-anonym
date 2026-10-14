# Baseline NER multilivello — run 1

## Perimetro

La baseline usa 46 conversazioni sintetiche e un gold di 35 annotazioni NER:
20 `PERSON` e 15 `LOCATION`. Tutti i modelli hanno completato 46 conversazioni
su 46, senza fallimenti tecnici. La soglia di GLiNER è 0,5.

## Risultati exact match

| Modello | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| GLiNER multilingual | 29 | 74 | 6 | 28,2% | 82,9% | 42,0% |
| GLiNER multilingual PII | 29 | 114 | 6 | 20,3% | 82,9% | 32,6% |
| WikiNEuRal | 31 | 7 | 4 | 81,6% | 88,6% | 84,9% |
| Piiranha | 31 | 2 | 4 | 93,9% | 88,6% | 91,2% |

Piiranha e WikiNEuRal sono le baseline più precise a soglia/configurazione
corrente. GLiNER mostra recall alto ma molti falsi positivi; non va descritto
semplicemente come modello inadeguato senza considerare soglia ed errori.

## Analisi di GLiNER multilingual

Dei 74 falsi positivi a soglia 0,5, 64 sono `PERSON` e 10 `LOCATION`. La classe
dominante è costituita da ruoli e riferimenti generici, soprattutto “referente”;
compaiono inoltre confini parziali di nomi, frammenti di email e locuzioni come
“unità locale” o “in questa sede”.

Una sweep retrospettiva sugli score salvati mostra che la soglia influisce molto:

| Soglia | F1 |
|---:|---:|
| 0,50 | 42,0% |
| 0,60 | 47,5% |
| 0,70 | 62,4% |
| 0,80 | 69,2% |
| 0,90 | 76,2% |
| 0,95 | 60,4% |

A 0,90 GLiNER multilingual raggiunge precision 85,7% e recall 68,6%. Questa è
un'analisi post hoc sul corpus di sviluppo, non una soglia validata: una futura
ottimizzazione richiede un development set separato dal test.

## Indirizzi e gold multilivello

Il gold iniziale rappresentava ogni indirizzo soltanto come `ADDRESS`, mentre
GLiNER separava correttamente strada+civico e comune. La versione multilivello
applica una regola definita indipendentemente dai modelli:

- l'indirizzo completo resta `ADDRESS` nel gold canonico;
- strada+civico è anche `LOCATION`;
- il comune è una seconda `LOCATION`.

Esempi correttamente rappresentati sono “Via Angelo Lauri 96” + “Nettuno” e
“Via Della Ruta 19” + “Anzio”. La revisione evita di premiare accidentalmente
un modello solo perché riproduceva la granularità del vecchio gold.

## Prestazioni computazionali

L'inferenza sulle 46 conversazioni ha richiesto circa 2,5–6,2 secondi per
modello; il picco VRAM osservato è stato circa 0,72–1,19 GB. Il costo rende
praticabile un benchmark sintetico più ampio.

## Secondo livello: protezione degli indirizzi

La valutazione post-hoc di copertura produce, sui soli due indirizzi disponibili:

| Modello | Completi | Copertura caratteri | Esito prevalente |
|---|---:|---:|---|
| GLiNER multilingual | 2/2 | 100,0% | completo |
| GLiNER multilingual PII | 0/2 | 0,0% | non coperto |
| WikiNEuRal | 0/2 | 90,5% | civico esposto |
| Piiranha | 0/2 | 28,6% | solo comune |

Questa analisi non sostituisce la metrica NER: mostra che gli errori di confine
hanno conseguenze operative diverse. Con due soli esempi è una verifica del
metodo, non una graduatoria affidabile. Il protocollo completo è descritto nella
[valutazione degli indirizzi](valutazione_indirizzi.md).

## Validità e passi successivi

Il campione è sintetico, piccolo e utilizzato durante lo sviluppo. I risultati
sono sufficienti come prova di fattibilità, non come stima definitiva della
generalizzazione. Il prossimo esperimento dovrà congelare un corpus più grande,
separare eventuale tuning e test, misurare esplicitamente la copertura degli
indirizzi e integrare il ramo regex prima di riportare metriche di pipeline.
