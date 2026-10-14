# Bootstrap delle metriche della run 3

## Obiettivo

Il bootstrap quantifica la variabilità delle metriche rispetto alla composizione
del corpus sintetico, senza rilanciare i modelli. Le predizioni della `run3`
restano congelate.

## Disegno

- unità di ricampionamento: conversazione completa;
- campionamento con reinserimento di 289 conversazioni;
- 10.000 repliche;
- seed `20261014`;
- intervalli percentile al 95%;
- stesso campione per tutti i modelli in ogni replica.

Il bootstrap è appaiato: turni, span e ripetizioni di uno stesso indirizzo
restano nello stesso cluster, mentre le differenze fra modelli sono calcolate
sulla medesima replica. Per ogni metrica sono salvati stima osservata, media
bootstrap, bias, varianza, errore standard ed estremi dell'intervallo.

Le metriche comprendono precision, recall e F1 micro, metriche per `PERSON` e
`LOCATION`, tasso di indirizzi completamente coperti e copertura dei caratteri
degli indirizzi. Il mean squared error non è utilizzato perché non è una misura
appropriata per questi esiti discreti e per l'F1.

## Esecuzione

```sh
.venv/bin/python src/bootstrap_metriche.py \
  --config config/bootstrap_paper_run3.json
```

Lo script non richiede GPU o accesso alla rete. Rifiuta di sovrascrivere output
esistenti e registra gli hash di configurazione, dataset, gold e predizioni.

## Output

- `output/bootstrap_ner_person_location_paper_300_run3/bootstrap.json`:
  risultati completi e differenze appaiate;
- `output/bootstrap_ner_person_location_paper_300_run3/riepilogo.md`:
  tabella sintetica pronta per la revisione.

## Limite interpretativo

Gli intervalli quantificano l'incertezza di campionamento condizionata al corpus
sintetico e al suo disegno di generazione. Non sono intervalli di
generalizzazione al traffico reale e non incorporano l'incertezza dovuta alla
scelta dei template, al modello generativo o al gold programmatico.
