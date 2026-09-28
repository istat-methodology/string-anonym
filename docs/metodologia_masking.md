# Metodologia di ricerca per il masking contestuale

Stato: proposta iniziale, 28 settembre 2026. Questo documento definisce gli
esperimenti da implementare; non descrive un sistema di masking già disponibile.

## Obiettivo e perimetro

Individuare e sostituire le porzioni identificative nelle conversazioni del
punto unico di contatto Istat, conservando le informazioni utili alla richiesta.
Riconoscere un nome o un luogo non basta: occorre decidere quale funzione abbia
nel contesto. Le decisioni già concordate sono in `casi_ambigui_masking.md`.
Il masking non costituisce, da solo, una garanzia di anonimizzazione complessiva.

Prima versione: PERSON, ADDRESS, EMAIL, PHONE, COD_UTENTE, PASSWORD e NUM_PRATICA.
Altre categorie, presenti nel prototipo storico, saranno introdotte solo con
regole di annotazione, esempi e valutazioni dedicati. Non dichiarare copertura
di codice fiscale, partita IVA, organizzazioni o altre categorie non valutate.

Esempi: un indirizzo personale va mascherato; il comune oggetto di una ricerca
statistica va conservato. Un codice utente va mascherato; un codice PSN pubblico
va conservato. Nomi bibliografici e contatti pubblici seguono le decisioni
contestuali concordate, non un'esclusione generale basata sul solo valore.

## Input e output

Unità operativa: messaggio corrente, ruolo e turni precedenti della stessa
conversazione. Niente turni futuri nella valutazione del funzionamento online.
Elaborare sia utente sia chatbot. Dichiarare e misurare l'eventuale limite di
contesto; non troncare silenziosamente i messaggi.

Il rilevatore riceve solo testi e ruoli. Scheda di generazione, slot, valori
campionati, trattamento atteso e riepilogo finale non sono input del modello.
Il riepilogo, se va mascherato come documento, richiede una valutazione separata.

Output: lista di span con campo, start incluso, end escluso, tipo, provenienza
del rilevatore e, dove disponibile, score. Le posizioni si riferiscono ai
caratteri Unicode del testo originale, coerentemente con le annotazioni locali.
La conversione token/caratteri deve essere verificata, anche con accenti e apostrofi.

## Architettura minima

1. Regex e modello leggono il testo originale e producono span candidati.
2. Una funzione combina i risultati e risolve sovrapposizioni con regole
   documentate e verificabili. Non mascherare due volte lo stesso intervallo.
3. La decisione contestuale distingue dati personali e riferimenti da conservare.
   Non assumere che ogni numero lungo sia telefono o partita IVA, né ogni data
   sia personale. Non trattare lo score del modello come probabilità calibrata.
4. La sostituzione deterministica applica gli span senza riscrivere altro testo.
   Gli identificativi, per esempio PERSON_1, restano coerenti nella conversazione
   e ripartono nella conversazione successiva. L'identità di due occorrenze non
   va dedotta da una semplice uguaglianza testuale in contesti incompatibili.

Nessun servizio separato necessario: poche funzioni con un formato comune.
Errori del rilevatore devono essere espliciti, non convertiti in esiti riusciti
con testo parzialmente mascherato. Conservare gli originali per la ricerca.

## Esperimenti

- R: baseline a regole, con formati e contesto locale espliciti.
- M: encoder preaddestrato a pesi aperti, adattato al riconoscimento degli span
  da mascherare. Confrontare messaggio isolato e contesto precedente.
- R+M: combinazione, sullo stesso test, per misurare il contributo delle regole.

Il vecchio modello di Samantha è un eventuale riferimento storico, non un
vincolo. Un modello generativo a pesi aperti è un confronto successivo, non
una dipendenza della prima versione. Nessun checkpoint è ancora selezionato:
verificare italiano, licenza, contesto, costo operativo e disponibilità dei pesi.
Ambiente di ricerca: A100 su Azure, presumibilmente 80 GB, da verificare.
Obiettivo successivo: esecuzione su infrastruttura Istat, con misure di memoria
e latenza anche sull'hardware effettivamente destinato al servizio.

## Dataset e separazione degli esperimenti

I lotti attuali sono materiale di sviluppo. Sono già stati letti e usati per
modificare i prompt: non sono un test finale indipendente. Lo stato `valido`
indica controlli automatici, non approvazione semantica delle annotazioni.

Conservare originali e revisioni separati. Escludere dal benchmark revisionato
gli scarti non risolti; registrare correzioni, autore della revisione e versione.
Controllare anche dati introdotti fuori dagli slot e falsi negativi nelle
conversazioni dichiarate senza dati personali.

Obiettivo iniziale indicativo: circa 1.000 conversazioni, dopo aver ampliato
le situazioni. Non è una soglia di sufficienza per il fine-tuning. Preparare
prima la separazione sviluppo/validazione/test, per famiglie di varianti e
conversazioni intere; mantenere insieme derivazioni e quasi duplicati. Seed
diversi, da soli, non garantiscono indipendenza. Il test finale deve usare
varianti nuove e non guidare successive modifiche senza essere riclassificato
come sviluppo. Registrare manifest, versioni e hash dei file.

Ampliare con negativi difficili, coppie contrastive (stessa forma, funzione
diversa), formati non visti, refusi, riferimenti tra turni, dati spontanei e
ripetizioni del chatbot. Misurare la copertura di queste caratteristiche.
Non confondere la distribuzione mirata con quella del traffico reale.
Un'eventuale valutazione su dati reali revisionati sarà una fase distinta,
necessaria prima di concludere sulla generalizzazione al servizio.

## Metriche e revisione

- Precision, recall e F1 sugli span esatti e sul tipo, globali e per categoria.
- Recall della copertura dei caratteri sensibili e caratteri conservabili
  rimossi erroneamente: rendono visibili errori parziali nei confini.
- Quota di conversazioni con almeno un dato personale non coperto.
- Falsi positivi sui negativi difficili e sui riferimenti pubblici.
- Coerenza delle sostituzioni fra turni e casi di identità erroneamente unite.
- Latenza, memoria e fallimenti operativi, con hardware e configurazione.

Riportare conteggi, denominatori, distinzione utente/chatbot e risultati per
scenario. Non chiamare il tasso di validazione del generatore accuratezza del
masking. Soglie e priorità fra omissioni e mascheramento eccessivo si concordano
sulla validazione, non sul test finale. Affiancare alle metriche una revisione
degli errori; ove possibile far annotare indipendentemente un sottoinsieme
e risolvere i disaccordi esplicitamente.

## Sequenza di implementazione

1. Esportazione senza informazioni sulle risposte attese nell'input, piccolo
   insieme revisionato e valutatore indipendente dal modello.
2. Baseline regex e sostituzione deterministica con test locali.
3. Catalogo ampliato, split e generazione a lotti eseguita dall'utente.
4. Selezione documentata del modello, fine-tuning ed esperimenti R/M/R+M.
5. Analisi degli errori e verifica operativa su infrastruttura Istat.

Non avviare download, generazioni o training come effetto della sola lettura
della configurazione. Credenziali fuori dai file versionati.
