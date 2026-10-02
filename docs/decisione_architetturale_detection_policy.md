# Separazione strutturale tra detection e policy

Stato: prima decisione implementativa, 2 ottobre 2026.

## Decisione

La pipeline separa tre step analitici:

1. la **detection del messaggio** riconosce elementi presenti nel testo;
2. la **policy di conversazione** usa l'intera chat come contesto e decide
   `KEEP`, `MASK`, `GENERALIZE` o `REVIEW` per ciascuna detection;
3. la **valutazione complessiva della conversazione** stima il rischio residuo
   dopo le decisioni puntuali.

I primi due step sono implementati nel prototipo. Il terzo non è ancora
implementato e avrà prompt, contratto e valutazione separati. La sostituzione di
`MASK` e `GENERALIZE` è un'operazione tecnica successiva, non uno step analitico.

Regex e NER ricevono lo stesso testo originale. Nessun detector riceve il testo
già modificato da un altro detector. I loro risultati sono combinati dalla
funzione `merge_detection`, che appartiene alla fase di detection e non applica
decisioni di masking.

## Contratto iniziale della detection

Ogni detection contiene campo, offset Unicode con fine esclusa, testo, tipo e
una o più sorgenti. Le sorgenti conservano almeno il detector e possono includere
regola, modello, score, versione ed etichetta nativa.

`merge_detection` unisce soltanto risultati con stesso campo, stessi offset e
stesso tipo, conservando tutte le sorgenti. Non elimina span sovrapposti e non
risolve disaccordi di tipo. Queste informazioni devono restare osservabili.

Gli offset canonici si riferiscono sempre al testo originale del messaggio. Se
un detector opera su singole frasi, i suoi offset locali devono essere riportati
al messaggio prima del merge.

L'elenco dei tipi supportati è operativo e versionabile. Non pretende di essere
una classificazione generale del dominio.

## Compatibilità transitoria

Gli output e i valutatori esistenti rappresentano span finali di masking e
richiedono intervalli non sovrapposti. Durante la migrazione gli script possono
produrre sia `detections`, nel nuovo formato, sia `annotazioni`, come adattatore
legacy. I risultati sperimentali esistenti restano invariati e sono descritti
come proxy end-to-end del masking.

## Prompt e annotazioni 5.0

Il prompt chat genera soltanto metadati e conversazione. Non produce detection,
decisioni o motivazioni. Il codice sostituisce gli slot e costruisce gli offset
attesi; anche i riferimenti pubblici controllati possono quindi entrare nel gold
di detection con un'ipotesi `KEEP` separata.

Il prompt policy riceve conversazione completa e detection, ma non le decisioni
attese. Produce una decisione contestuale per ogni detection. Le ipotesi sono
conservate fuori dai messaggi con stato `APPROVED`, `PROVISIONAL` o `OPEN`; i
casi `OPEN` non costituiscono gold definitivo. Una valutazione aggregata del
rischio residuo della conversazione è rinviata a un esperimento separato.

I nuovi esperimenti useranno output distinti e non sovrascriveranno quelli storici.
La policy corrente non restituisce un giudizio aggregato sulla conversazione.

## Perimetro rinviato

La valutazione sull'intero dataset e i dati sanitari non fanno parte della prima
implementazione. Potranno essere aggiunti con una decisione successiva senza
modificare il contratto della detection a livello di messaggio.
