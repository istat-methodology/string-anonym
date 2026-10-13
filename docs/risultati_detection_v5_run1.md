# Risultati esplorativi detection 5.0 — run 1

## Ruolo della run

Questa è una run pilota su 46 conversazioni sintetiche e 202 detection attese.
Serve a verificare runner, mapping e fattibilità computazionale. Non è il
benchmark finale e non va usata per ottimizzare e poi dichiarare prestazioni
indipendenti sullo stesso corpus.

La configurazione iniziale chiedeva a GLiNER tredici categorie. L'architettura
chiarita dopo la run assegna invece al NER la responsabilità primaria di
`PERSON` e `LOCATION`; le categorie strutturate sono affidate al ramo regex o a
lookup controllati. Di conseguenza la metrica globale della run è diagnostica.

## Metrica primaria ricalcolata: PERSON + LOCATION

| Modello | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| GLiNER multilingual | 17 | 90 | 14 | 15,9% | 54,8% | 24,6% |
| GLiNER multilingual PII | 24 | 116 | 7 | 17,1% | 77,4% | 28,1% |
| WikiNEuRal | 29 | 9 | 2 | 76,3% | 93,5% | 84,1% |
| Piiranha | 26 | 4 | 2 | 86,7% | 92,9% | 89,7% |

Piiranha ha completato 44 conversazioni su 46; le sue metriche escludono due
fallimenti tecnici e non hanno quindi lo stesso denominatore degli altri modelli.
Il runner successivo ignora e registra gli span composti soltanto da spazi,
invece di scartare l'intera conversazione.

WikiNEuRal e Piiranha mostrano prestazioni elevate nel focus previsto. I valori
GLiNER non sono ancora una misura pulita del task `PERSON`–`LOCATION`, perché la
run gli chiedeva contemporaneamente undici ulteriori categorie e ha prodotto
molti falsi positivi. La configurazione successiva interroga tutti i modelli
soltanto sulle due categorie assegnate al NER.

## Metrica globale diagnostica

| Modello | Precision | Recall | F1 | Conversazioni valutate |
|---|---:|---:|---:|---:|
| GLiNER multilingual | 23,5% | 36,1% | 28,5% | 46/46 |
| GLiNER multilingual PII | 24,8% | 55,0% | 34,2% | 46/46 |
| WikiNEuRal | 41,2% | 17,3% | 24,4% | 46/46 |
| Piiranha | 54,7% | 15,8% | 24,6% | 44/46 |

Questi valori penalizzano i modelli per categorie che non costituiscono il loro
compito architetturale. Non rappresentano la prestazione futura della pipeline
riconciliata. La metrica globale di sistema sarà calcolata sulle detection unite
di regex e NER dopo `merge_detection`.

## Prestazioni computazionali

I tempi di inferenza sulle 46 conversazioni variano da circa 2,5 a 8,7 secondi.
Il picco di VRAM osservato varia da circa 0,72 a 1,19 GB. Il costo consente quindi
di ampliare il benchmark e di eseguire analisi ripetute senza un carico elevato.

## Decisioni successive alla run

1. Conservare immutati gli output della run 1.
2. Aggiungere ai report `tipi_focus_ner: [PERSON, LOCATION]`.
3. Eseguire la configurazione `esperimento_ner_person_location_v5.json`, nella
   quale anche le etichette richieste a GLiNER sono limitate al focus.
4. Implementare e verificare il ramo regex sulle categorie assegnate.
5. Valutare separatamente componente NER e pipeline riconciliata.
