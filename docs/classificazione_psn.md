# Classificazione di lavoro del catalogo PSN

Aggiornamento locale del 27 settembre 2026. Le 159 coppie codice–denominazione
originali sono conservate. Sono aggiunti `tipo_rispondente`,
`fonte_classificazione` e `nota_classificazione`.

| Tipo | Righe |
|---|---:|
| imprese | 42 |
| famiglie_individui | 25 |
| altro | 16 |
| da_verificare | 76 |

La fonte principale è [psn_2.pdf](psn_2.pdf). Il documento ordina i lavori per
ente titolare e area statistica; non contiene una colonna famiglie/imprese.
La classificazione derivata dal titolo è pertanto un’inferenza di lavoro,
indicata come tale in ogni riga. L’area socio-demografica non implica
automaticamente che rispondano famiglie: il soggetto osservato e il compilatore
possono essere diversi. I casi incerti restano `da_verificare`.

Per alcune righe è stata usata anche la colonna «Soggetti sanzionabili» di
[psn_1.pdf](psn_1.pdf), che esplicita imprese o istituzioni. Tale evidenza serve
solo a distinguere la tipologia: non viene usata per produrre indicazioni
sull’obbligo o sulle sanzioni e non descrive necessariamente tutte le unità
coperte dall’indagine. Le pagine nel CSV sono numeri di pagina PDF, a partire da 1.
`altro` comprende istituzioni e strutture non riconducibili alle due categorie
principali; non è sinonimo di pubblica amministrazione.

Per modificare una decisione basta aggiornare la riga del CSV insieme alla
motivazione e alla fonte. Non viene eseguita una classificazione automatica
basata su parole chiave durante la generazione.

## Associazioni iniziali del pilota

`config/scenari.json` contiene liste esplicite di codici ammessi, controllate
contro il tipo del rispondente. Sono proposte per il pilota da revisionare.
Per accesso e facsimile sono selezionabili IST-00070 e IST-01175; per il caso
specifico di compilazione industriale soltanto IST-00070. Gli altri tre casi
restano senza riferimento a un’indagine specifica.

Il codice 01677/CVTS del catalogo precedente non è stato riutilizzato come
corrispondenza PSN: non compare nei due documenti con quel codice. Il riferimento
IAP-00006 (INDACO - CVTS) non è stato assunto equivalente. Le chiavi del portale
rimangono null, indipendenti dal codice PSN.

La categoria del rispondente, da sola, non basta per scegliere un’indagine:
una selezione indiscriminata potrebbe introdurre temi sanitari o indagini
incompatibili con la situazione. Le liste ammesse evitano questo problema.
