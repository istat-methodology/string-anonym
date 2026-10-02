# Casi ambigui per detection e policy

Convenzioni approvate da Mauro il 27 settembre 2026 per il progetto.
I valori sono esempi di simulazione. L’approvazione riguarda le decisioni
di annotazione riportate qui; non implica che tutte siano già implementate.
Gli span includono soltanto la parte in grassetto. Le decisioni valgono anche
se il chatbot ripete la menzione o la descrizione la riporta.

| Testo | Decisione concordata | Motivo / limite |
|---|---|---|
| Cerco la popolazione del comune di Roma nel 2024. | Conservare Roma e 2024. | Territorio e periodo della richiesta statistica. |
| Scrivo per conto del **Comune di Roma**. | ORG sull’intera denominazione. | L’ente si identifica come richiedente. |
| Ho consultato una pubblicazione dell’Istat. | Conservare Istat. | Fonte pubblica, non identità del richiedente. |
| Sono **Anna Rossi**, della **Rossi Servizi S.r.l.**. | PERSON e ORG separati. | Due menzioni distinte, senza sovrapposizione. |
| Scrivo per la **Ditta individuale Anna Rossi**. | Un solo span ORG. | Nessun PERSON annidato nella denominazione. |
| Sono **Anna Rossi**. Potete richiamare la signora **Rossi**? | Due span PERSON, stessa identità se il contesto conferma il riferimento. | La forma breve deve essere assegnata esplicitamente, non trovata per sottostringa. |
| Il precedente referente è **Anna Rossi**; io sono **Luca Bianchi**, il mio recapito è **luca.bianchi@example.org**. | Due PERSON e un EMAIL. | L’email appartiene al nuovo referente. |
| Spedite a **Via Roma 12, Latina**. | ADDRESS sull’intero indirizzo. | Destinazione identificativa; Roma non è qui un territorio statistico. |
| Il mio Prot.n. **1589563/25** riguarda il questionario. | NUM_PRATICA sul solo valore. | Formato provvisorio; Prot.n. escluso. |
| Cerco informazioni su IST-00070, Rilevazione annuale della produzione industriale (Prodcom). | Conservare codice e nome. | Il codice PSN identifica l’indagine. Non dedurre la chiave del portale. |
| Scrivetemi a **contatto.123456@example.org**. | EMAIL. | Recapito del richiedente. |
| Per assistenza, usi [recapito pubblico verificato]. | Conservare il contatto solo con fonte approvata. | Esempio schematico: non inventare recapiti istituzionali nei lotti. |
| Sto cercando una pubblicazione di Mario Rossi. | Conservare Mario Rossi quando il contesto chiarisce che è l’autore di una pubblicazione pubblica. | Riferimento bibliografico pubblico; non identità del richiedente o di un suo referente. Convenzione approvata da Mauro. |

Nei test della pipeline gli esempi territoriali devono comparire anche insieme a
entità personali: «Sono Anna Rossi e cerco dati sulla popolazione di Roma»
maschera la persona e conserva il territorio. Questa nota non costituisce una
nuova modalità di generazione.

La conservazione del nome dell’autore richiede un contesto chiaro di riferimento
a una pubblicazione pubblica. Non si estende automaticamente a qualsiasi nome
menzionato in una ricerca. «Sono Mario Rossi» resta PERSON; i contesti incerti
richiedono revisione.

## Punti ancora aperti

- Il formato del numero di pratica resta provvisorio; è concordata l’esclusione
  di `Prot.n.` dallo span.
- I contatti istituzionali si conservano quando verificati su una fonte approvata;
  occorre ancora disporre dei recapiti da usare nei lotti.
- Le organizzazioni coinvolte in acquisizioni, fusioni o cambi di ragione sociale
  vengono rilevate, ma l'azione tra `MASK`, `GENERALIZE` e `REVIEW` resta `OPEN`
  fino al confronto con il management. Nell'esperimento
  `conversation-draft-2` il modello ha scelto `GENERALIZE` in una conversazione
  e `MASK` nelle altre tre varianti dello stesso scenario: il risultato conferma
  che non va fissata automaticamente una regola.
- Le ipotesi non approvate non entrano nelle metriche come gold definitivo.

## Separazione nei nuovi prompt

Il generatore realizza il caso contrastivo ma non assegna decisioni. Gli span
attesi sono costruiti localmente. Un prompt distinto valuta poi la conversazione
completa: cambiare una convenzione non richiede di rigenerare automaticamente la chat.
La valutazione complessiva del rischio residuo della conversazione resta un terzo
step futuro e non fa parte del prompt di policy corrente.
