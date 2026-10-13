# Confronto dei modelli NER

`src/confronta_modelli.py` esegue i modelli in sequenza sugli stessi messaggi e
valuta `PERSON` e `LOCATION` con exact match di confini e tipo. Ogni messaggio è
processato isolatamente: il modello non riceve gold, metadati descrittivi, turni
successivi o decisioni di policy.

## Modelli

| Modello | Backend | Licenza dichiarata dei pesi |
|---|---|---|
| GLiNER multilingual | `gliner` | Apache-2.0 |
| GLiNER multilingual PII | `gliner` | Apache-2.0 |
| WikiNEuRal | Transformers | CC-BY-NC-SA-4.0 |
| Piiranha | Transformers | CC-BY-NC-ND-4.0 |

La disponibilità dei pesi non implica che ogni licenza sia compatibile con ogni
uso. In particolare, le varianti non commerciali richiedono una verifica prima
di impieghi diversi dal confronto di ricerca.

La configurazione corrente è
`config/esperimento_ner_person_location_v5_multilivello.json`. Contiene
repository, revisione, soglia, limite di token, mapping delle etichette e output.
Le revisioni `main` vengono risolte in hash e registrate nel manifest della run.

## Normalizzazione

- gli offset sono riferiti al testo originale;
- gli spazi esterni prodotti dal tokenizer vengono rimossi;
- le etichette native sono convertite in `PERSON` o `LOCATION`;
- le etichette escluse sono conteggiate, non convertite;
- output nativi e score sono sempre conservati;
- overlap e disaccordi restano disponibili nel campo `detections`;
- gli score di modelli diversi non sono confrontati tra loro.

## Esecuzione

Controllo senza rete né inferenza:

```sh
.venv/bin/python src/confronta_modelli.py --solo-controllo
```

Run su GPU:

```sh
python src/confronta_modelli.py --device cuda:0
```

Il percorso `output` della configurazione deve essere nuovo. Se CUDA non è
disponibile, il runner fallisce senza passare silenziosamente alla CPU. I modelli
sono caricati uno alla volta; un errore di caricamento non impedisce di tentare
i modelli successivi.

## Output

La directory della run contiene configurazione e manifest globali, più una
sottocartella per modello con:

- `predizioni.jsonl`: formato comune;
- `predizioni_native.jsonl`: output originale per messaggio;
- `valutazione.json`: metriche e dettagli degli errori;
- `manifest.json`: modello, revisione, mapping, tempi, memoria ed errori.

`riepilogo.json` raccoglie stato, metriche, durata e picchi VRAM. I fallimenti
tecnici sono esclusi dalle metriche e vanno sempre riportati insieme al numero
di conversazioni valutate.

## Limiti

Il confronto misura soltanto la componente NER della detection. Non misura il
ramo regex, `merge_detection`, la policy contestuale o l'anonimizzazione finale.
Il corpus è sintetico, piccolo e di sviluppo; le prestazioni non sono una stima
indipendente su conversazioni reali. Per gli indirizzi va aggiunta una misura di
copertura dei caratteri, perché l'exact match non quantifica direttamente quanto
testo identificativo resterebbe esposto.
