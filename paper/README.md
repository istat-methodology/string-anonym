# Materiali per lo short paper

Questa cartella raccoglie una base condivisibile per la scrittura dello short
paper. I testi distinguono risultati osservati, interpretazioni metodologiche e
sviluppi futuri. Non sostituiscono gli artefatti eseguibili della repository:
configurazioni, manifest, dataset esportati e predizioni restano le fonti
primarie per la riproducibilità.

## Struttura proposta

1. **Introduzione e related work** — da sviluppare con il gruppo di lavoro.
2. [Costruzione del dataset sintetico](01_dataset_sintetico.md) — scenari,
   generazione controllata, varianti degli indirizzi e controllo qualità.
3. [Metodologia e pipeline](02_metodologia_pipeline.md) — separazione fra
   detection e policy, gold, protocollo sperimentale e metriche.
4. [Modelli NER e ramo regex](03_modelli_ner_e_regex.md) — modelli confrontati,
   configurazioni, licenze, normalizzazione e ruolo degli identificativi
   strutturati.
5. [Risultati e discussione](04_risultati_e_discussione.md) — exact match,
   valutazione degli indirizzi, esempi qualitativi, limiti e implicazioni.

## Messaggio centrale emerso

Il benchmark non identifica un modello *one-size-fits-all*. Nell'esperimento
principale definitivo (`run3`), Piiranha ottiene il miglior equilibrio
exact-match sia complessivo sia per `PERSON` e `LOCATION`. GLiNER PII raggiunge
invece la massima copertura operativa degli indirizzi, ma produce una forte
tendenza al mascheramento oltre i confini del gold `PERSON`–`LOCATION`.
L'exact match aggregato non è quindi sufficiente a
rappresentare il rischio residuo: una valutazione per componenti mostra se
civico, interno, strada o comune restano visibili e rende esplicito il
trade-off fra esposizione residua e contenuto aggiuntivo mascherato.

## Perimetro dello short paper

Il lavoro valuta la detection a livello di messaggio. La policy a livello di
conversazione, l'applicazione del masking e la valutazione complessiva del
rischio non sono implementate in questo esperimento. Il ramo regex è descritto
come componente architetturale per gli identificativi strutturati, ma i
risultati quantitativi correnti riguardano soltanto `PERSON` e `LOCATION`.

## Numeri di riferimento

- 300 conversazioni sintetiche generate;
- 289 conversazioni validate e incluse nel benchmark;
- 11 conversazioni escluse in modo tracciato;
- 123 annotazioni `PERSON` e 296 `LOCATION`;
- 124 occorrenze di indirizzo valutate;
- quattro modelli, 289/289 conversazioni elaborate e zero fallimenti tecnici.
- `run3` come esperimento principale definitivo; `run1` e `run2` conservate
  soltanto come traccia dell'evoluzione metodologica e analisi di ablazione.

