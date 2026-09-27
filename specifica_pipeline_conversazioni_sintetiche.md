# Pipeline per la generazione di conversazioni sintetiche del Contact Centre Istat

Versione 0.4 — 27 settembre 2026  
Stato: specifica di lavoro per il confronto con i colleghi e per la successiva implementazione.

Questo documento aggiorna la specifica Word `specifica_dataset_sintetico_masking_rev2.docx` con le decisioni concordate nel progetto. Il Word resta conservato. Le sezioni che descrivono la pipeline prevista non implicano che tutte le funzionalità siano già implementate: lo stato del software è riepilogato nella sezione 10.

## 1. Obiettivo e perimetro

Preparare un dataset di conversazioni sintetiche per sviluppare e valutare un motore di mascheramento delle chat del Punto Unico di Contatto Istat. Il mascheramento precede l'archiviazione e l'analisi delle conversazioni, che serviranno soprattutto a valutare le risposte del chatbot e, in secondo luogo, a studiare l'utilizzo del sistema.

Occorre proteggere gli elementi identificativi senza eliminare le informazioni necessarie a comprendere la richiesta e valutare la risposta. Per esempio, il nome di un comune richiesto per una tabella statistica deve poter restare leggibile; lo stesso nome, nella denominazione di un ente che si identifica come rispondente, può appartenere a un'entità da mascherare.

Il dataset deve contenere conversazioni sia con sia senza entità da mascherare, oltre a casi difficili che somigliano a identificativi ma devono essere conservati. Le risposte simulate del chatbot non costituiscono una fonte ufficiale sulle procedure Istat.

La generazione utilizza scenari, cataloghi locali e materiali operativi approvati. Non richiede di inviare conversazioni reali all'endpoint generativo.

## 2. Decisioni concordate

| Tema | Decisione |
|---|---|
| Unità di generazione | Una chiamata al modello produce una conversazione. |
| Modalità | `con_dati_personali` e `senza_dati_personali`; la modalità `misto` non viene usata nei nuovi lotti. |
| Significato delle modalità | Presenza o assenza delle entità da mascherare secondo questa specifica; non una certificazione generale di assenza di informazioni sensibili. |
| Ambito del mascheramento | Tutti i messaggi, sia utente sia chatbot, comprese ripetizioni e citazioni. Anche un'eventuale descrizione contenente identificativi deve essere trattata. |
| Origine dei valori | Campionamento locale da nomi, cognomi, codici dei comuni, `strade_lazio.csv` e `codici_psn.csv`; generatori locali a regole per gli altri identificativi. Nessun Faker in questa fase. |
| Compito del modello | Generare il dialogo usando i segnaposto assegnati, senza inventare ulteriori identità o credenziali. |
| Variazione delle entità | Non assegnare sempre lo stesso insieme a ogni scenario: campionare combinazioni plausibili. |
| Annotazioni | Span contigui e non sovrapposti, ricavati localmente dalla sostituzione dei segnaposto. |
| Modelli | Un solo modello può generare training, development e test sintetico. Il confronto fra generatori è un'estensione successiva. |
| Riproducibilità | Conservare prompt, configurazione, dati di partenza, seed e modello; non richiedere risposte identiche tra chiamate successive. |
| Metadati esclusi | Canale, dipartimento, classificazione del revisore, conversazione analizzata, esito/nota operatore, soddisfazione dell'utente. |
| Complessità | Procedere per piccoli lotti verificati, evitando infrastrutture non necessarie. |

## 3. Evidenze disponibili e loro limiti

I conteggi del Word, le lunghezze e le percentuali devono essere verificati prima di usarli come risultati di una pubblicazione. In particolare, distinguere sempre un **messaggio** da uno **scambio**, cioè una coppia utente–chatbot.

La baseline descritta nel Word combina espressioni regolari e BERT con categorie ampie per nomi e indirizzi. I punti da verificare nel confronto sono soprattutto codici numerici ambigui, identificativi brevi o rumorosi, luoghi mascherati fuori contesto, date e contatti pubblici rimossi inutilmente, confini imprecisi delle entità. Il fatto che una menzione compaia nel turno del chatbot non è di per sé un motivo per conservarla.

## 4. Catalogo degli scenari

La tassonomia del Word viene mantenuta come base. Le entità indicate nelle tabelle sono esempi plausibili, non un obbligo di inserirle tutte. Il simbolo `—` indica che la richiesta tipica può essere priva di identificativi, non che questi siano impossibili.

Tipologie di utente: **I** imprese, **F** famiglie, **C** cittadini, **P** pubbliche amministrazioni e scuole, **R** ricercatori e università, **M** media. Sono caratteristiche della scheda di generazione, non identità reali.

### 4.1 Assistenza ai rispondenti

| ID | Area | Scenario | Utenti | Entità plausibili |
|---|---|---|---|---|
| A01 | Accesso e navigazione | Problemi di accesso | I, P, F | COD_UTENTE, PASSWORD, EMAIL, COD_UNITA |
| A02 | Accesso e navigazione | Uso delle deleghe | I, P | PERSON, EMAIL, CF, PASSWORD |
| A03 | Accesso e navigazione | Difficoltà d'uso dei portali | I, P | COD_UTENTE, ORG |
| A04 | Aspetti normativi | Normativa e obbligo | I, F, P | ORG, NUM_PRATICA |
| A05 | Aspetti normativi | Privacy e conservazione dei dati | F, I | PERSON, CF |
| A06 | Aspetti normativi | Comunicazione dei dati | I, P | ORG |
| A07 | Composizione del campione | Informazioni sul campione | F, I | PERSON, ADDRESS |
| A08 | Composizione del campione | Impossibilità a partecipare | F, I | PERSON, PHONE |
| A09 | Composizione del campione | Lingua straniera | F | PERSON, PHONE, ADDRESS |
| A10 | Composizione del campione | Assenza prolungata | F | PERSON, ADDRESS |
| A11 | Composizione del campione | Calamità naturali | F, I | ADDRESS, ORG |
| A12 | Composizione del campione | Rifiuto o indisponibilità | F, I | PERSON, ORG |
| A13 | Prenotazione intervista | Prenotazione dell'intervista | F | PERSON, PHONE, ADDRESS |
| A14 | Accertamenti e sanzioni | Accertamenti e sanzioni | I, F | NUM_PRATICA, ORG, PIVA, CF |
| A15 | Indagine e questionario | Calendario | Tutti | — |
| A16 | Indagine e questionario | Facsimile del questionario | I, P | — |
| A17 | Indagine e questionario | Identificazione del rilevatore | F | PERSON, PHONE |
| A18 | Indagine e questionario | Modalità di partecipazione | F, I | — |
| A19 | Indagine e questionario | Informazioni specifiche sull'indagine | I, F, P | ORG, ADDRESS |
| A20 | Indagine e questionario | Problemi di invio del questionario | I, P | COD_UTENTE, NUM_PRATICA |
| A21 | Indagine e questionario | Durata del questionario | F | — |
| A22 | Indagine e questionario | Modifica dei dati precompilati | I, P | ORG, PIVA, ADDRESS |
| A23 | Indagine e questionario | Ricevuta | I, P | NUM_PRATICA, COD_UNITA |
| A24 | Indagine e questionario | Salvataggio parziale | I, P | COD_UTENTE |
| A25 | Indagine e questionario | Stato del questionario | I, P | COD_UNITA, NUM_PRATICA |
| A26 | Indagine e questionario | Riapertura del questionario | I, P | COD_UNITA, ORG |
| A27 | Comunicazione con Istat | Lamentela | Tutti | PERSON, EMAIL, PHONE |
| A28 | Comunicazione con Istat | Informativa, sollecito o promemoria | I, F | NUM_PRATICA, ORG, ADDRESS |

La voce relativa a malattie gravi resta fuori da questa fase. L'impossibilità a partecipare può essere simulata senza introdurre condizioni sanitarie.

### 4.2 Altri servizi del Contact Centre

| ID | Servizio | Scenario | Utenti | Entità plausibili |
|---|---|---|---|---|
| B01 | Assistenza ricerca dati | Dove trovare un dato | Tutti | — |
| B02 | Assistenza ricerca dati | Dati territoriali fini: comune o sezione | P, R, I | PERSON, EMAIL, ORG |
| B03 | Assistenza ricerca dati | Definizioni, metodologia e differenze fra fonti | R, M, C | — |
| B04 | Assistenza ricerca dati | Calendario di diffusione e prossimo rilascio | M, R | — |
| B05 | Dati storici | Serie lunghe e censimenti storici | R, C | — |
| B06 | Dati storici | Cartografia e basi territoriali storiche | P, R | ORG |
| B07 | Dati europei | Dati Eurostat e confronti UE | R, M | — |
| B08 | Dati europei | Differenze fra Istat ed Eurostat | R, M | — |
| B09 | Rilascio microdati | File disponibili: MFR, file per la ricerca, ADELE | R | — |
| B10 | Rilascio microdati | Requisiti e modulistica | R | PERSON, EMAIL, ORG |
| B11 | Rilascio microdati | Stato della richiesta e allegati | R | NUM_PRATICA, EMAIL, ORG |
| B12 | Rilascio microdati | Accesso al laboratorio ADELE | R | PERSON, NUM_PRATICA, ORG |
| B13 | Elaborazioni personalizzate | Tabelle ad hoc | P, I, R | PERSON, EMAIL, ORG |
| B14 | Elaborazioni personalizzate | Costi, preventivo e tempi | I, P | ORG, PIVA, EMAIL |
| B15 | Elaborazioni personalizzate | Stato dell'elaborazione | Tutti | NUM_PRATICA, ORG |
| B16 | Acquisto volumi | Disponibilità e ordine | C, R, I | PERSON, ADDRESS, ORG |
| B17 | Acquisto volumi | Spedizione | C, I | ADDRESS, PHONE, NUM_PRATICA |
| B18 | Acquisto volumi | Fatturazione | I, P | ORG, PIVA, CF, ADDRESS, EMAIL |
| B19 | Supporto media | Verifica di un dato per un articolo | M | PERSON, PHONE, EMAIL, ORG |
| B20 | Supporto media | Intervista a un esperto | M | PERSON, PHONE, ORG |
| B21 | Sportello cittadini | Rivalutazione FOI di affitto o assegno | C | — |
| B22 | Sportello cittadini | Certificazione ufficiale degli indici | C, I | PERSON, NUM_PRATICA |
| B23 | Sportello cittadini | Informazioni su Istat, concorsi e tirocini | C | PERSON, EMAIL |
| B24 | Sportello cittadini | Accesso ai propri dati | C | PERSON, CF, ADDRESS |
| B25 | Segnala un errore | Errore in tavola, dataset o pubblicazione | Tutti | PERSON, EMAIL |
| B26 | Segnala un errore | Errore sul sito o collegamento non funzionante | Tutti | — |
| B27 | Invia un reclamo | Disservizio o tempi di risposta | Tutti | PERSON, EMAIL, PHONE, NUM_PRATICA |


Il catalogo contiene 28 voci A e 27 voci B, per un totale di 55 scenari. Test, saluti e richieste fuori perimetro non costituiscono scenari del catalogo. Il totale del futuro catalogo va comunque calcolato dai dati, senza incorporare nel codice il conteggio riportato nel Word. Gli ID di questa specifica sono riferimenti editoriali: la corrispondenza con gli identificativi del software dovrà essere definita nell'implementazione.

## 5. Entità e politica di mascheramento

Il criterio è il ruolo della menzione nella conversazione, non soltanto la sua forma. Le seguenti sono le etichette previste; il software attuale ne gestisce solo un sottoinsieme con nomi diversi.

| Etichetta | Contenuto da mascherare | Confine previsto |
|---|---|---|
| PERSON | Nomi e cognomi di persone: utente, delegato, referente, rilevatore, operatore, ecc. | Intera menzione inserita; se compare solo il cognome, solo quel cognome. |
| ORG | Organizzazione che si identifica come richiedente o rispondente, incluse ditte individuali ed enti pubblici | Denominazione completa, senza entità PERSON annidate. |
| EMAIL | Recapito della persona o dell'organizzazione richiedente | Indirizzo email completo. |
| PHONE | Recapito telefonico identificativo | Numero con prefisso e separatori presenti. |
| ADDRESS | Indirizzo postale identificativo, completo o parziale, di residenza, sede o spedizione | Intero valore inserito nello slot dell'indirizzo. |
| CF | Codice fiscale personale | Codice presente nel testo. |
| PIVA | Partita IVA o codice fiscale numerico dell'organizzazione | Valore completo, compreso l'eventuale prefisso IT. |
| COD_UNITA | Identificativo Istat dell'unità rispondente | Solo il valore identificativo. |
| COD_UTENTE | Codice di accesso o nome utente | Solo il valore identificativo. |
| PASSWORD | Credenziale riportata nella chat | Solo il valore della credenziale. |
| NUM_PRATICA | Numero di protocollo, richiesta, pratica o ticket | Solo il valore, senza introduzioni come «Prot. n.». |

Esempio: in `Prot. n. 1234567/25`, lo span NUM_PRATICA è `1234567/25`. In una denominazione di ditta individuale che include nome e cognome, si usa un unico span ORG. Gli span sono piatti, contigui e non sovrapposti.

La stessa entità ripetuta dall'utente o dal chatbot conserva il proprio identificativo logico; ogni occorrenza riceve uno span distinto. Varianti come nome completo e solo cognome richiedono forme esplicitamente associate alla stessa entità: non affidare questa associazione a una ricerca indiscriminata di sottostringhe.

### Informazioni da conservare e casi difficili

Aggiornamento del 27 settembre 2026: Mauro ha approvato le decisioni raccolte
nei [casi ambigui](docs/casi_ambigui_masking.md). Il documento distingue le
convenzioni concordate dai punti ancora aperti. È concordata anche la
conservazione del nome quando il contesto lo identifica chiaramente come autore
di una pubblicazione pubblica. L’approvazione non equivale all’implementazione
di tutte le categorie nel software.

- Nomi di indagini, chiavi d'indagine e codici PSN, quando identificano la rilevazione e non l'utente.
- Codici ATECO, Prodcom o doganali usati come classificazioni.
- Luoghi usati per chiedere dati territoriali, senza funzione di indirizzo identificativo.
- Organizzazioni citate come fonti statistiche o riferimenti pubblici.
- Contatti istituzionali pubblici usati per orientare l'utente, distinguendoli dai recapiti del richiedente.
- Date, anni, scadenze, importi e quantità statistiche, secondo il perimetro attuale del progetto.

Ad esempio, «cerco le presenze turistiche nel comune di Roma» conserva Roma; «scrivo per conto del Comune di Roma» può identificare l'organizzazione richiedente e quindi richiedere ORG. In «cerco una pubblicazione di Mario Rossi», conservare il nome quando il contesto chiarisce che identifica l’autore di una pubblicazione pubblica. In «sono Mario Rossi», annotare il nome come PERSON. La conservazione non si estende automaticamente a qualsiasi nome usato come oggetto di ricerca: i contesti incerti richiedono revisione.

I casi difficili, o *hard negative*, devono comparire anche nelle conversazioni con entità da mascherare. Non costituiscono una terza modalità. Una chat senza entità può comunque contenere nomi di luoghi, codici, date e cifre da conservare.

I dati sanitari sono fuori da questa fase. Anche informazioni economiche e altri contenuti non coperti dalle etichette possono avere rilevanza per la riservatezza: la copertura NER qui definita non equivale a una garanzia generale di anonimato.

## 6. Struttura di un esempio

Tenere distinti i dati di controllo della generazione dalla conversazione destinata alle analisi.

**Scheda di generazione:** identificativo dell'esempio, versione del catalogo e del prompt, scenario, sezione del servizio, tipologia di utente, modalità, lingua, stile, lunghezza indicativa, indagine pertinente, entità e forme ammesse, riferimenti da conservare, seed e split assegnato.

**Metadati della conversazione:** `data_sintetica`, `chiave_indagine` e `descrizione`. La chiave è una stringa, per preservare eventuali zeri iniziali, oppure `null`. La descrizione deve riassumere ciò che è effettivamente emerso e non trasformare ipotesi del chatbot in fatti.

Il campo `canale` viene escluso dal formato previsto. Tutte le richieste sono considerate provenienti dal Contact Centre. Le richieste relative al Portale imprese rientrano negli scenari di accesso e di informazione sulle rilevazioni delle imprese; non richiedono un canale distinto. Il codice corrente dovrà essere allineato a questa decisione.

**Conversazione:** sequenza ordinata di messaggi con ruolo e testo. Sono ammessi messaggi brevi, codici isolati, refusi e una conclusione dell'utente dopo la risposta del chatbot. La lunghezza richiesta è indicativa; non aggiungere scambi vuoti o artificiali per raggiungere un numero.

**Trattamento atteso:** alla fine di ogni esempio, elenco delle entità da mascherare con tutte le occorrenze, riferimenti significativi da conservare e una breve motivazione nei casi ambigui. Le annotazioni devono riferirsi al testo finale, comprese le risposte del chatbot e l'eventuale descrizione.

**Provenienza:** prompt completo, scheda, modello/deployment, parametri effettivamente inviati, data di esecuzione, risposta originale, versione della validazione, esiti e correzioni applicate. Le credenziali API non fanno parte dell'output.

## 7. Pipeline prevista

### 7.1 Lettura e preparazione degli input

Leggere cinque input locali, preparando liste ordinate e strutture riutilizzabili dal sampling:

| Input | Struttura da preparare | Utilizzo |
|---|---|---|
| Nomi | Lista di nomi unici | Campionamento delle persone. |
| Cognomi | Lista di cognomi unici | Combinazione con i nomi campionati. |
| Codici dei comuni | Mappa codice ISTAT–comune, mantenendo anche il codice catastale disponibile | Coerenza geografica e supporto alla generazione dei codici fiscali. |
| `data/strade_lazio.csv` | Coppie uniche comune–odonimo, usando `CODICE_ISTAT`, `COMUNE`, `ODONIMO` | Campionamento della strada e del comune associato. |
| `data/codici_psn.csv` | Coppie codice–nome, usando `codice_psn` e `nome_indagine` | Campionamento coerente del riferimento all'indagine. |

Normalizzare spazi e rappresentazione dei caratteri, gestire l'eventuale BOM UTF-8 e mantenere tutti i codici come stringhe. I due CSV indicati usano il punto e virgola come separatore. Rimuovere i duplicati esatti; segnalare valori mancanti e associazioni contrastanti, senza scegliere arbitrariamente un nome per lo stesso codice.

Per gli indirizzi, partire direttamente da `strade_lazio.csv`: il file originale con tutti i civici non è più un input della pipeline prevista. Campionare la strada insieme al comune e generare successivamente il civico. Non occorre ripetere a ogni esecuzione il trattamento dell'archivio voluminoso.

Il catalogo PSN contiene attualmente 159 righe con codice e nome valorizzati. Questo conteggio descrive il file disponibile, non è un vincolo del parser. Campionare sempre la coppia dalla stessa riga, senza far inventare al modello associazioni tra codici e indagini. Il file non contiene informazioni sufficienti a dedurre obblighi, scadenze o sanzioni.

Il parser corrente legge ancora gli input precedenti: l'uso diretto dello stradario compatto e l'integrazione del catalogo PSN sono modifiche da implementare dopo l'aggiornamento della specifica.

### 7.2 Campionamento della scheda e dei valori

Scegliere scenario, modalità e caratteristiche linguistiche, quindi un sottoinsieme plausibile delle entità. Campionare nome e cognome dalle rispettive liste e la strada insieme al suo comune. Il civico sintetico non deve essere presentato come un indirizzo verificato.

Le email possono usare `example.org`. Se un nuovo referente scrive a proposito di un precedente referente, non derivare automaticamente l'email del primo dal nome del secondo: mantenere separate le identità.

Quando lo scenario riguarda un'indagine, campionare codice e nome da `codici_psn.csv`, scegliendo fra le indagini compatibili con il caso. Una piccola associazione esplicita fra scenari, tipo di rispondente e indagini può essere concordata con i colleghi; il CSV non fornisce da solo questa classificazione. Negli scenari non pertinenti, non forzare un riferimento all'indagine. I codici PSN sono informazioni da conservare, non entità identificative da mascherare. Mantenere distinto il codice PSN da un'eventuale chiave specifica del portale, senza assumere equivalenza.

Per gli identificativi aggiuntivi usare generatori locali semplici, controllati dal seed, senza Faker. Il file `src/anonymisation_model_BERT_advanced.py` offre formati ed esempi utili come punto di partenza:

| Entità | Generazione prevista |
|---|---|
| PHONE | Numeri sintetici nei formati previsti, con varianti di prefisso internazionale e separatori. Il sorgente mostra forme compatte, con spazi e con punti. |
| CF | Generatore dedicato con struttura e carattere di controllo corretti; coerenza con nome e cognome campionati e con attributi sintetici di nascita. Usare il codice catastale, non il codice ISTAT del comune. Gli attributi di nascita servono al generatore e non devono necessariamente comparire nel dialogo. |
| PIVA | Generatore dedicato di valori di 11 cifre con cifra di controllo corretta, eventualmente rappresentati con prefisso IT. |
| COD_UTENTE | Formati presenti nel sorgente: `P0` seguito da 8 cifre; tre lettere seguite da almeno 5 cifre, ad esempio con prefisso QOL; sequenze numeriche di almeno 7 cifre presentate come codice utente. Usare lunghezze finite configurate per il sampling. |
| COD_UNITA, NUM_PRATICA | Formati distinti associati al significato dello scenario, concordati con i colleghi; non classificare un numero soltanto dalla lunghezza. |
| PASSWORD | Stringhe sintetiche generate localmente, con lunghezze e caratteri configurati. |
| ORG | Piccoli cataloghi o composizioni controllate, coerenti con il tipo di organizzazione richiedente. |

Le espressioni regolari del sorgente riconoscono forme superficiali e non verificano da sole la validità di CF o PIVA. Per COD_UTENTE, il commento con l'esempio `P012345678` non coincide con la regola `P0` + 8 cifre: per il generatore si adotta la regola esplicita, con esempio coerente `P0123456789`. Questi sono formati di simulazione, non una descrizione esaustiva degli account del servizio.

Generare prima valori conformi, poi eventuali varianti rumorose dichiarate nella scheda. Non usare credenziali effettive. La conformità formale non implica che un identificativo sia assegnato; allo stesso modo, il campionamento non garantisce che nomi, recapiti o codici non coincidano accidentalmente con valori esistenti.

### 7.3 Generazione del dialogo

Costruire un prompt dinamico a partire dalla scheda e chiedere una sola conversazione. Il modello deve usare i segnaposto assegnati in tutti i campi testuali pertinenti, anche quando il chatbot ripete un identificativo. I valori proposti possono accompagnare gli slot come nel pilota attuale, ma la risposta deve mantenere i segnaposto.

Il prompt deve richiedere naturalezza, coerenza fra messaggi e descrizione, rispetto della modalità e nessun identificativo aggiuntivo inventato. Non obbligare il chatbot a chiedere dati personali per rendere positivo un esempio: l'utente può inserirli spontaneamente. Le istruzioni devono distinguere i riferimenti statistici da conservare dalle identità da mascherare.

Le risposte operative e normative devono restare generiche quando manca una fonte approvata. Integrare successivamente FAQ o indicazioni concordate per evitare che il generatore inventi procedure, obblighi o scadenze.

### 7.4 Sostituzione locale e costruzione degli span

Validare prima la struttura con i segnaposto. Sostituire poi ogni slot con il valore campionato e registrare la posizione di ciascuna sostituzione mentre si costruisce il testo finale. Questo evita di chiedere al modello di calcolare gli offset.

Convenzione proposta: `start` incluso e `end` escluso, misurati in caratteri Unicode secondo l'indicizzazione delle stringhe Python, relativamente al singolo campo testuale. Ogni annotazione identifica il messaggio o il campo di metadati, l'etichetta, l'entità logica e il testo coperto. Deve valere sempre `testo[start:end] == valore_annotato`.

Eventuali alterazioni intenzionali dei valori, come O/0, spazi o separatori, devono essere definite prima del calcolo definitivo degli offset. Annotare la forma realmente presente. Non modificare successivamente i testi senza ricalcolare le annotazioni.

La sostituzione rende esatti i confini degli slot, ma non dimostra che tutte le entità siano state individuate: identificativi inventati fuori dagli slot e contesti semanticamente errati richiedono controlli separati.

### 7.5 Validazione e salvataggio

Controllare almeno struttura, testi non vuoti, ruoli, metadati, slot riconosciuti, presenza delle entità previste, assenza di slot residui, integrità degli span e coerenza della modalità. Verificare inoltre che descrizione e trattamento atteso non aggiungano fatti assenti dalla conversazione.

Salvare ogni risultato in JSONL: ogni riga è un oggetto JSON completo relativo a una conversazione, mentre gli a capo interni ai messaggi sono codificati nel JSON. Il formato facilita lettura progressiva e salvataggio dei risultati man mano che arrivano.

Conservare gli esempi `da_verificare` e le risposte originali; non correggere il significato della chat per far passare un controllo. L'etichetta `valido` indica il superamento dei controlli implementati, non la revisione umana completa.

Prima dei lotti ampi, aggiungere la ripresa da output esistente tramite identificativi stabili, con controllo che il lotto e la configurazione coincidano. Non rigenerare automaticamente gli esempi già completati. Il salvataggio progressivo attuale è utile, ma non costituisce ancora una funzione di ripresa.

## 8. Copertura, volumi e suddivisione dei dati

Iniziare con un piccolo lotto per gruppi di scenari, verificare le conversazioni e ampliare solo dopo aver corretto problemi ricorrenti. Per ogni voce, chiedere ai colleghi di validare pochi casi rappresentativi e rivedere le lacune per guidare l'espansione.

Le quantità del Word restano **ipotesi da calibrare**, non requisiti già approvati né distribuzioni implementate:

| Parametro | Proposta del Word | Come usarla |
|---|---|---|
| Esempi per cella | 60 training, 10 development, 15 test bilanciato | Calcolare i totali dal numero effettivo C di celle: 60C, 10C, 15C. |
| Conversazioni senza entità | 20% nelle celle con entità tipiche; 90% nelle altre | La percentuale globale dipende dai pesi delle celle; non fissare automaticamente un totale del 35–40%. |
| Hard negative | Almeno metà delle conversazioni; circa 10% con organizzazioni citate da conservare | Verificare plausibilità e definire il denominatore delle quote. |
| Copertura delle etichette | Almeno 300 occorrenze per etichetta nel training | Contare anche conversazioni e contesti distinti: ripetizioni nella stessa chat non danno la stessa varietà. |
| Lingue | Tutti i casi della voce lingua straniera; 30% microdati/dati UE; 3% altrove | Quote esplorative, da confrontare con evidenze del servizio. |
| Test con distribuzione operativa | Circa 850 chat, 40% accesso | Scenario sperimentale proposto, non stima verificata del traffico reale. |

Per le lingue, inglese e, in misura minore, tedesco e francese per dati europei e microdati. Prevedere anche cambi di lingua all'interno della chat, se plausibili.

Separare training, development e test a livello di conversazione. Varianti derivate dalla stessa conversazione di base devono restare nello stesso insieme. Utilizzare un solo modello generativo è compatibile con questa separazione; non elimina però la somiglianza stilistica fra i dati sintetici.

Per il test reale, riservare un periodo successivo non usato per progettare o correggere il sistema, mantenendo intere le conversazioni. Le prime tre settimane di un mese per lo sviluppo e una quarta per il test sono una possibile organizzazione, da adattare al volume e alla stagionalità. Se un test viene usato per arricchire il dataset, diventa parte del ciclo di sviluppo: occorre un nuovo insieme finale indipendente.

Gli originali annotati internamente sono necessari per misurare falsi negativi e falsi positivi reali. Si può usare un solo modello per generare il sintetico; un riferimento reale affidabile richiede comunque annotazioni controllate e non soltanto le predizioni dello stesso modello valutato.

## 9. Riproducibilità essenziale

Per ogni lotto conservare la versione di questa specifica, il catalogo, i prompt, il seed locale, i riferimenti alle versioni dei cinque input e delle regole di campionamento, il modello/deployment e i parametri API effettivi. Conservare anche output, validazione ed eventuali revisioni.

Il seed permette di ripetere le scelte locali a parità di input e codice. Il modello può produrre dialoghi diversi in esecuzioni successive: è accettabile. La pubblicazione deve permettere di ricostruire il metodo e comprendere i dati usati, senza promettere identità delle risposte.

Il deployment usato nel pilota è `gpt-5.6-terra` e `claude-sonnet-5` su Azure Foundry.

## 10. Stato del progetto al momento della specifica

**Aggiornamento implementativo successivo (incremento 4.0, 27 settembre 2026):**
la tabella seguente conserva lo stato iniziale del progetto. Lo stato corrente,
le parti implementate e quelle ancora previste sono nel [README](README.md).
Sono ora disponibili lettura dei cinque input con solo stradario compatto,
classificazione PSN con fonti, metadati senza canale, prime regole configurabili
e span locali. Il catalogo resta limitato ai sei casi pilota; la specifica
non è ancora interamente implementata.

| Componente | Stato attuale | Lavoro previsto |
|---|---|---|
| Input | Parser degli input precedenti; stradario compatto e catalogo PSN disponibili | Leggere direttamente `strade_lazio.csv` e integrare `codici_psn.csv` nel sampling. |
| Metadati | Il formato corrente include ancora `canale` | Rimuovere il campo; assumere Contact Centre come contesto comune. |
| Catalogo | Sei scenari: accesso, ricerca questionario, compilazione, precedente referente, residenza, dati territoriali | Tradurre progressivamente la tassonomia di questa specifica in configurazione. |
| Modalità | Due modalità e sottoinsieme variabile delle entità | Calibrare pesi e copertura per scenario. |
| Entità | PERSONA, EMAIL e INDIRIZZO con sostituzione locale | Migrare a PERSON/ADDRESS ed estendere alle altre etichette senza Faker. |
| Prompt | Versione 3.1; 24 esempi nel lotto pilota: 6 × 2 modalità × 2 esempi | Estendere slot, forme, scenari e annotazioni. |
| Endpoint | Una chiamata Responses per conversazione su Foundry | Mantenere tracciato il deployment utilizzato nei diversi lotti. |
| Output | Risposta originale, template, chat con valori e trattamento atteso | Aggiungere span esatti per ogni occorrenza e campo pertinente. |
| Validazione | Controlli strutturali, normalizzazioni limitate e alcuni segnali lessicali di incoerenza | Controlli degli span, nuove etichette e revisione semantica campionaria. |
| Salvataggio | Progressivo; file esistente non sovrascritto | Ripresa del lotto e gestione degli errori prima di aumentare molto i volumi. |
| Ultimo lotto consolidato | 24 chat che superano i controlli correnti | Revisione del contenuto; non considerarlo già un benchmark completo. |

Riferimenti nel repository:

- [Parser degli input](src/parse_input.py).
- [Generazione dei prompt](src/genera_prompt.py) e [catalogo corrente](config/scenari.json).
- [Invocazione dell'endpoint](src/genera_chat.py).
- [Rivalidazione locale](src/rivalida_chat.py).
- [Lotto pilota consolidato](output/chat_lotto_v3_1_consolidato.jsonl).
- [Istruzioni operative e cronologia delle versioni](README.md).

Il lotto consolidato comprende 23 conversazioni rivalidate e una rigenerata. Il superamento dei controlli correnti non certifica la correttezza di tutte le risposte né l'assenza di identificativi non previsti.

Attenzione alle versioni: il generatore di chat ha ancora come input predefinito il lotto v2; per usare un lotto successivo occorre specificarne il percorso. `--limit` indica il numero massimo di conversazioni da elaborare, non il numero di esempi nel prompt né un limite del servizio. Nome e documentazione dell'opzione potranno essere resi più chiari nell'aggiornamento del codice.

## 11. Punti da chiarire e prossima implementazione

Prima di estendere il codice, concordare con i colleghi:

1. La corrispondenza fra eventuali chiavi del portale e codici PSN, senza assumere che siano lo stesso identificativo.
2. Le associazioni fra indagini del CSV, scenari e tipi di rispondente.
3. I formati di unità e pratiche e le eventuali ulteriori varianti dei codici utente, partendo dalle regole del sorgente.
4. Le fonti approvate per descrizioni delle indagini, FAQ e risposte operative: il catalogo dei codici non autorizza a dedurre obblighi o sanzioni.
5. Completare i punti aperti delle [convenzioni concordate](docs/casi_ambigui_masking.md): disponibilità di contatti istituzionali verificati. Le decisioni sugli enti pubblici richiedenti, sui contatti pubblici verificati e sui nomi chiaramente riferiti ad autori di pubblicazioni pubbliche sono state approvate da Mauro il 27 settembre 2026.

La sequenza proposta per il lavoro successivo è: aggiornare gli input e rimuovere il canale; introdurre catalogo e politica delle etichette; estendere i valori locali; aggiornare prompt e span per l'intera chat; produrre e revisionare piccoli lotti; aggiungere la ripresa; ampliare i volumi. IBAN, targhe e ulteriori categorie restano estensioni eventuali, non requisiti di questa fase.

Per riprendere il progetto in una nuova sessione, partire da questo documento e dalla sezione 10, controllare lo stato effettivo dei file e mantenere separate le decisioni concordate dalle quote sperimentali. La redazione di questa specifica non modifica il codice né avvia nuove chiamate al modello.
