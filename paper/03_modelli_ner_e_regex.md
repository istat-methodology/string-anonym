# Modelli NER e ramo regex

## Modelli confrontati

| Nome nel benchmark | Repository | Backend | Licenza dichiarata dei pesi |
| --- | --- | --- | --- |
| GLiNER multi | `urchade/gliner_multi-v2.1` | GLiNER | Apache-2.0 |
| GLiNER PII | `urchade/gliner_multi_pii-v1` | GLiNER | Apache-2.0 |
| WikiNEuRal | `Babelscape/wikineural-multilingual-ner` | Transformers | CC-BY-NC-SA-4.0 |
| Piiranha | `iiiorg/piiranha-v1-detect-personal-information` | Transformers | CC-BY-NC-ND-4.0 |

La disponibilità pubblica dei pesi non implica compatibilità con ogni uso. In
particolare, le licenze non commerciali richiedono una valutazione separata
prima di un eventuale impiego di prodotto. Nel presente lavoro i modelli sono
usati per confronto di ricerca.

## Configurazione comune

Tutti i modelli sono valutati su `PERSON` e `LOCATION`. Non è stato effettuato
fine-tuning sul corpus. GLiNER riceve le etichette testuali `person` e
`location` con soglia 0,5 e limite di 384 token. WikiNEuRal e Piiranha usano le
etichette native mappate nelle due categorie comuni; le altre etichette vengono
ignorate ma conteggiate.

| Modello | Etichette native utilizzate | Soglia | Limite token |
| --- | --- | ---: | ---: |
| GLiNER multi | `person`, `location` | 0,5 | 384 |
| GLiNER PII | `person`, `location` | 0,5 | 384 |
| WikiNEuRal | `PER`, `LOC` | nativa | 512 |
| Piiranha | `GIVENNAME`, `SURNAME`, `CITY` | nativa | 256 |

Per Piiranha nome e cognome adiacenti vengono uniti in uno span `PERSON`. Gli
score di architetture diverse non sono confrontati direttamente. Non è stata
condotta una ricerca delle soglie sui 289 esempi; un'eventuale calibrazione
richiederà una separazione esplicita fra development e test set.

## Perché quattro modelli

Il confronto include modelli con obiettivi diversi:

- GLiNER multi consente etichette espresse in linguaggio naturale ed è
  orientato alla generalizzazione fra schemi;
- GLiNER PII è una variante focalizzata sulle informazioni personali;
- WikiNEuRal è una baseline NER multilingue tradizionale;
- Piiranha è un modello dedicato al riconoscimento di categorie PII.

Il disegno non assume che un singolo modello debba essere il migliore per tutte
le categorie. I risultati confermano una specializzazione: Piiranha è più
efficace su `PERSON`, mentre GLiNER multi protegge molto meglio gli indirizzi.

## Ruolo del ramo regex

NER e regex leggono indipendentemente il testo originale. Il ramo regex è
destinato agli identificativi con forma controllabile o cataloghi affidabili,
tra cui:

- telefono ed email;
- codice indagine e nome dell'indagine tramite lookup;
- numero pratica e altri codici strutturati;
- password nei contesti e nei formati previsti;
- ruoli istituzionali quando definiti da un lessico controllato.

`PERSON` e `LOCATION` restano responsabilità primaria del NER. Questa
assegnazione non implica che le regex raggiungano automaticamente il 100%:
pattern e lookup devono essere valutati sul loro specifico benchmark.

La futura funzione `merge_detection` deve unire soltanto detection compatibili
per campo, offset e tipo, conservando le fonti concordanti. Sovrapposizioni e
conflitti non devono essere cancellati silenziosamente. Un esempio rilevante è
la parola `referente`: GLiNER multi la classifica frequentemente come `PERSON`,
mentre il ramo controllato può identificarla come `ROLE` e rendere esplicito il
disaccordo.

## Perimetro quantitativo corrente

Lo short paper riporta metriche quantitative per il solo confronto NER
`PERSON`–`LOCATION`. Il ramo regex è già separato nell'architettura e dispone di
regole versionate, ma non viene presentato come baseline quantitativa completa
finché la sua copertura non sarà congelata e valutata. Analogamente, non sono
ancora misurati il merge, la policy conversazionale o il masking finale.

## Riproducibilità

La run registra revisioni dei modelli, versioni delle librerie, device, hash
degli input, tempi e memoria. I quattro modelli hanno completato l'intero
benchmark senza fallimenti. La configurazione e i manifest sono disponibili in:

- `config/esperimento_ner_person_location_paper_300.json`;
- `output/confronto_ner_person_location_paper_300_run1/manifest.json`;
- sottocartelle di ciascun modello con predizioni native, predizioni
  normalizzate, valutazione e manifest.

