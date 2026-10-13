# Ramo regex della detection

Il ramo regex riconosce identificativi strutturati sul testo originale del
messaggio. Le regole operative sono in `config/regole_masking.json`; sono
distinte dalle regole usate per generare valori sintetici.

Il perimetro previsto comprende telefono, codice indagine, nome indagine, ruolo,
numero pratica e altri identificativi dalla forma controllabile. `PERSON` e
`LOCATION` restano responsabilità primaria del ramo NER.

Esecuzione su un dataset esportato:

```sh
.venv/bin/python src/predici_regex.py \
  --input output/dataset_detection_v5_draft4_multilivello/input.jsonl \
  --output output/predizioni_regex_NOME_RUN
```

L'output deve essere nuovo. Le predizioni regex e NER dovranno poi essere unite
da `merge_detection`, che combina solo detection con campo, offset e tipo
identici e conserva fonti, overlap e conflitti.

La copertura delle regole non è ancora validata sul benchmark corrente. Non si
assume quindi una precisione o recall del 100%: prima dello short paper occorre
definire il mapping delle categorie, produrre le predizioni e misurare sia il
ramo regex sia il risultato riconciliato.
