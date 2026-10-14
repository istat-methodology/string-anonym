# Risultati detection sul corpus paper — run 3 definitiva

## Perimetro

Il corpus sorgente contiene 300 conversazioni sintetiche. Il controllo qualità
ne ha validate 289 ed escluse 11; le esclusioni sono registrate nel dataset.
Il benchmark contiene 123 span `PERSON` e 296 span `LOCATION`. Tutti e quattro
modelli hanno valutato 289/289 conversazioni senza fallimenti tecnici.

Questi risultati descrivono un corpus sintetico di sviluppo, non un test finale
indipendente su conversazioni reali e non un gold revisionato da annotatori
umani.

### Disegno sperimentale e controllo qualità

Le conversazioni sono state generate da scenari controllati separando tre
responsabilità: il modello generativo produce il dialogo con segnaposto, il
codice inserisce i valori sintetici e costruisce gli offset, mentre il gold di
detection viene derivato dagli slot e dai riferimenti noti. Il modello che
genera il testo non decide quindi quali span debbano essere riconosciuti o
mascherati. Questa separazione riduce la circolarità tra generazione e
valutazione, pur non sostituendo un'annotazione umana indipendente.

Le 11 conversazioni escluse non sono errori API: non hanno superato i controlli
locali di struttura o coerenza. Sono state conservate in `esclusi.jsonl` e non
sono entrate nelle metriche. Non sono state corrette manualmente né promosse a
valide per raggiungere una numerosità prefissata. Il tasso di inclusione è
289/300 (96,3%).

Il campionamento degli indirizzi è intenzionalmente più ricco rispetto alla loro
ipotetica prevalenza nel traffico reale. Si tratta di uno stress test orientato
al rischio, non di una stima della distribuzione operativa delle richieste. Le
varianti includono indirizzi completi, senza tipo di strada, senza civico, senza
comune, con civico complesso e con interno o scala.

I modelli sono valutati nelle configurazioni riportate nei manifest, senza
fine-tuning sul corpus. GLiNER multi riceve le etichette testuali `person` e
`location`; GLiNER PII riceve anche `address`, mappata a `LOCATION`.
WikiNEuRal usa `PER` e `LOC`. Per Piiranha, `GIVENNAME` e `SURNAME` sono mappate
a `PERSON`, mentre `STREET`, `BUILDINGNUM` e `CITY` sono mappate a `LOCATION`.
Le sequenze native strada–civico vengono ricomposte senza fondere il comune. Le
soglie non sono state ottimizzate sui 289 esempi: per GLiNER è usata 0,5,
mentre per i modelli token-classification è mantenuto il comportamento nativo.

La `run3` è l'esperimento principale definitivo. La configurazione iniziale
della `run1` ometteva `STREET` e `BUILDINGNUM` per Piiranha e non interrogava
GLiNER PII con `address`; i risultati di quella run non vengono pertanto usati
per la classifica principale. La `run2` è conservata come ablazione di GLiNER
multi con l'etichetta aggiuntiva `address`.

## Exact match

| Modello | Precision | Recall | F1 | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GLiNER multi | 0,465 | **0,924** | 0,619 | 387 | 445 | 32 |
| GLiNER PII | 0,198 | 0,465 | 0,278 | 195 | 791 | 224 |
| WikiNEuRal | 0,633 | 0,666 | 0,649 | 279 | 162 | 140 |
| Piiranha | **0,865** | 0,888 | **0,876** | 372 | 58 | 47 |

### Metriche per categoria

| Modello | PERSON P | PERSON R | PERSON F1 | LOCATION P | LOCATION R | LOCATION F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GLiNER multi | 0,251 | **0,951** | 0,397 | 0,740 | **0,912** | **0,817** |
| GLiNER PII | 0,207 | **0,976** | 0,342 | 0,184 | 0,253 | 0,213 |
| WikiNEuRal | 0,719 | 0,813 | 0,763 | 0,593 | 0,605 | 0,599 |
| Piiranha | **0,904** | 0,919 | **0,911** | **0,849** | 0,875 | **0,862** |

Piiranha ottiene il miglior exact-match complessivo e il miglior F1 sia su
`PERSON` sia su `LOCATION`. GLiNER multi conserva il recall micro più elevato,
ma con 445 falsi positivi. La bassa precisione `PERSON` di GLiNER multi è
concentrata soprattutto su termini di
ruolo: tra i falsi positivi ricorrono `referente` 143 volte, `precedente
referente` 36 volte e `Il precedente referente` 15 volte.

### Come leggere l'exact match

L'exact match considera corretta una predizione soltanto quando tipo, messaggio,
inizio e fine dello span coincidono con il gold. È una metrica rigorosa e
riproducibile, ma tratta allo stesso modo due errori operativamente diversi:
uno span quasi coincidente che copre comunque l'informazione sensibile e una
mancata detection che la lascia completamente esposta. Per questo motivo viene
usato come baseline NER, non come unica misura dell'efficacia di
anonimizzazione.

Il confronto aggregato mescola inoltre due comportamenti molto diversi.
GLiNER privilegia il recall e produce molti falsi positivi; Piiranha raggiunge
un equilibrio molto migliore fra precisione e recall. La scelta operativa non
può comunque essere derivata dal solo F1 micro quando il costo di una mancata
detection è diverso dal costo di un mascheramento eccessivo.

### Errori sistematici su PERSON

I 350 falsi positivi `PERSON` di GLiNER multi sono fortemente concentrati su
termini funzionali ricorrenti nei dialoghi: `referente`, `precedente referente`,
`delegato`, `destinatario` e, più raramente, `responsabile`. Il dato suggerisce
una confusione sistematica fra persona e ruolo, coerente con il dominio
istituzionale, piuttosto che una degradazione uniforme del riconoscimento dei
nomi propri.

La frequenza assoluta di questi errori è amplificata dalla ripetizione degli
stessi concetti nei template sintetici e non va interpretata come prevalenza
nel traffico reale. È però direttamente utile per la progettazione: il ramo
regex o una fase di riconciliazione può riconoscere lessici di ruolo senza
modificare la capacità del modello di trovare nomi propri. Qualsiasi filtro
andrà valutato separatamente per evitare di rimuovere veri nomi coincidenti con
termini comuni.

## Valutazione operativa degli indirizzi

La valutazione post-hoc misura la copertura degli stessi span predetti, senza
modificarli. Sono valutate 124 occorrenze di indirizzo.

Il numero indica le occorrenze nei messaggi, non gli indirizzi unici assegnati
alle schede: lo stesso valore può essere ripreso dall'Agente o ricomparire in un
turno successivo. Ogni occorrenza viene valutata perché una ripetizione non
riconosciuta lascerebbe comunque esposto il dato.

Il gold canonico conserva l'intero `ADDRESS` e, quando presenti, due viste NER
annidate: la parte stradale con eventuale civico e il comune come `LOCATION`.
Questa rappresentazione evita di imporre che un modello debba necessariamente
restituire l'indirizzo come un unico span. Un output che separa correttamente
strada e comune può quindi essere operativamente valido anche se non coincide
con un'unica annotazione `ADDRESS` legacy.

La valutazione operativa calcola l'unione dei caratteri dell'indirizzo coperti
dalle predizioni `LOCATION`. Non corregge, espande o riconcilia le predizioni:
è una seconda vista sugli stessi output. Un indirizzo è `complete` solo quando
tutti i suoi caratteri alfanumerici risultano coperti. Sono riportati anche la
copertura per componente e il testo residuo che resterebbe visibile.

Nel seguito questa vista è indicata come **copertura dell'indirizzo invariante
rispetto alla segmentazione**: non richiede che strada, civico e comune siano
restituiti con lo stesso numero di span del gold, purché la loro unione protegga
l'intero indirizzo. La metrica non viene usata per sostituire o ricalcolare
l'F1 exact-match.

| Modello | Indirizzi completi | Tasso completo | Copertura caratteri | Esposizione residua |
| --- | ---: | ---: | ---: | ---: |
| GLiNER multi | 120/124 | 0,968 | 0,983 | 0,017 |
| GLiNER PII | **122/124** | **0,984** | **0,986** | **0,014** |
| WikiNEuRal | 16/124 | 0,129 | 0,792 | 0,208 |
| Piiranha | 92/124 | 0,742 | 0,915 | 0,085 |

### Copertura completa per componente

| Componente | N | GLiNER multi | GLiNER PII | WikiNEuRal | Piiranha |
| --- | ---: | ---: | ---: | ---: | ---: |
| Strada | 124 | 121 | **122** | 111 | 109 |
| Civico | 110 | 107 | **108** | 4 | 102 |
| Interno/scala | 17 | **17** | **17** | 0 | 0 |
| Comune | 105 | **105** | 103 | 98 | **105** |

GLiNER PII copre integralmente 122/124 indirizzi e tutte le 17 occorrenze con
interno o scala. GLiNER multi segue a breve distanza con 120/124. Piiranha
riconosce molto bene strada, civico e comune, ma non copre completamente nessuno
dei 17 interni; WikiNEuRal lascia frequentemente visibile il numero civico.

### Interpretazione degli indirizzi

Il risultato sul campione ampio conferma che la configurazione delle etichette
è parte sostanziale del protocollo. GLiNER può coprire l'indirizzo come span
ampio `address` oppure come più `LOCATION`; Piiranha usa invece etichette native
più fini. La revisione del protocollo non è stata introdotta per “salvare” un
modello, ma per evitare che un mapping incompleto fosse interpretato come un
limite del modello e per allineare la valutazione al rischio osservabile.

GLiNER PII raggiunge la migliore copertura degli indirizzi, ma non è il miglior
modello exact-match: uno span ampio può proteggere tutto il valore senza
coincidere con le due annotazioni gold strada+civico e comune. Inoltre, la sua
copertura del 98,6% si accompagna a 9.016 caratteri esterni agli span gold
`PERSON`–`LOCATION` e a predizioni considerate false positive in 123 delle 163
conversazioni negative rispetto a queste due categorie. Questi caratteri non
sono necessariamente tutti innocui: il conteggio include anche email e altri
identificativi esclusi dal benchmark NER perché destinati al ramo regex. La
metrica misura quindi l'espansività rispetto al gold in esame, non direttamente
la perdita finale di utilità dopo la riconciliazione.

### Cosa significa che GLiNER PII è “aggressivo”

L'aggressività osservata comprende almeno tre fenomeni, con implicazioni
operative diverse.

| Fenomeno | Esempio della `run3` | Lettura operativa |
| --- | --- | --- |
| Span ampio desiderabile | Gold: `Via Casal Di Zaino 109` + `Cisterna di Latina`; predizione: `Via Casal Di Zaino 109, Cisterna di Latina` come unica `LOCATION` | L'exact match penalizza i confini diversi, ma il masking dell'intero span protegge correttamente l'indirizzo. |
| Altra PII fuori dal focus NER | `mariagiovanna.deaddis@example.org` classificata `PERSON` | È un falso positivo rispetto al gold `PERSON`–`LOCATION`, ma l'email dovrebbe comunque essere rimossa dal ramo regex; non implica necessariamente una perdita indebita di utilità. |
| Rumore semantico reale | `assistenza` classificata `PERSON`; `recapito` classificato `LOCATION`; `Sono delegato` classificato `PERSON` | Questi span non identificano una persona o un luogo specifici e il loro masking impoverirebbe inutilmente il dialogo. |

Un secondo esempio favorevole è `Via La Foresta 169, interno 7, Anagni`, che
GLiNER PII restituisce come un unico span `LOCATION` completo. Per l'obiettivo
di produzione — impedire che civico e interno restino visibili — questo
comportamento è conservativo e potenzialmente appropriato. Il problema non è
quindi l'ampiezza dello span in sé, ma l'incapacità di distinguere in modo
affidabile uno span ampio sensibile da termini generici come `assistenza` o
`recapito`.

La valutazione suggerisce pertanto di non scartare GLiNER PII sulla sola base
della precisione exact-match. In una pipeline di produzione potrebbe essere
usato come detector ad alto recall per gli indirizzi, seguito da
riconciliazione, filtri per ruoli e termini generici, oppure da una policy che
accetti span conservativi soltanto quando presentano segnali strutturali di
indirizzo. Questa ipotesi resta da verificare end-to-end.

Il caso `Via Casal Di Zaino 109, Cisterna di Latina` sintetizza il risultato:
il gold rappresenta strada+civico e comune come due `LOCATION`, mentre GLiNER
PII restituisce una sola `LOCATION` che coincide con l'indirizzo completo. Per
un compito NER con exact match le rappresentazioni sono diverse; per il
masking dell'indirizzo sono funzionalmente equivalenti. Il divario fra F1
exact-match e copertura invariante alla segmentazione è quindi un risultato
del benchmark, non soltanto una limitazione della metrica.

| Caso non completamente coperto da GLiNER multi | Esito | Testo residuo |
| --- | --- | --- |
| `Giovanni Agnelli 185, Minturno` | solo comune | `Giovanni Agnelli 185` |
| `Della Faterna 248, Poli` — messaggio utente | civico esposto | `248` |
| `Della Faterna 248, Poli` — ripetizione Agente | solo comune | `Della Faterna 248` |
| `Via Giuseppe Garibaldi, Ferentino` | solo comune | `Via Giuseppe Garibaldi` |

WikiNEuRal raggiunge una copertura media dei caratteri relativamente alta ma
solo 16 indirizzi completamente coperti: la differenza è dovuta soprattutto a
civici e interni lasciati visibili. Con il mapping completo, Piiranha sale da
0/124 a 92/124 indirizzi completi: il precedente risultato era un artefatto del
protocollo, non una proprietà del modello. Restano però scoperti gli interni.
Il risultato mostra concretamente perché mapping, exact match e copertura del
dato sensibile devono essere documentati e interpretati separatamente.

### Esempi comparativi sugli indirizzi

Gli esempi seguenti includono una forma per ciascuna variante del piano. Sono
stati selezionati fra i casi in cui GLiNER multi copre il 100% dell'indirizzo e
WikiNEuRal non lo copre integralmente. La colonna “residuo” riporta i caratteri
alfanumerici che rimarrebbero visibili secondo la valutazione operativa; non è
una ricostruzione manuale delle predizioni.

| Variante ed esempio | GLiNER multi | GLiNER PII | WikiNEuRal | Piiranha |
| --- | --- | --- | --- | --- |
| Completo: `Via Casal Di Zaino 109, Cisterna di Latina` | **100%**, nessun residuo | **100%**, nessun residuo | 91,2%, residuo `109` | **100%**, nessun residuo |
| Senza tipo di strada: `Giovanni Agnelli 185, Minturno` | **100%**, nessun residuo | **100%**, nessun residuo | 30,8%, residuo `Giovanni Agnelli 185` | 42,3%, residuo `Giovanni Agnelli` |
| Senza civico: `Traversa Prima Vigne Inferiori, Santi Cosma e Damiano` | **100%**, nessun residuo | **100%**, nessun residuo | 40,0%, residuo `Traversa Prima Vigne Inferiori` | **100%**, nessun residuo |
| Senza comune: `Via Colle Sant'Upica 28` | **100%**, nessun residuo | **100%**, nessun residuo | 89,5%, residuo `28` | **100%**, nessun residuo |
| Civico complesso: `Via Silvio Pellico 198 bis, Antrodoco` | **100%**, nessun residuo | **100%**, nessun residuo | 80,6%, residuo `198 bis` | **100%**, nessun residuo |
| Con interno: `Via La Foresta 169, interno 7, Anagni` | **100%**, nessun residuo | **100%**, nessun residuo | 62,1%, residuo `169, interno 7` | 75,9%, residuo `interno` |

Questi casi chiariscono il diverso comportamento dei modelli. WikiNEuRal
riconosce spesso strada e comune ma esclude il civico o l'interno dal confine
dello span. Piiranha, una volta mappate tutte le etichette native pertinenti,
copre molti indirizzi standard e con civico complesso, ma resta debole sugli
interni e su alcune forme senza tipo di strada. I due GLiNER includono invece le
componenti in uno o più span la cui unione copre quasi sempre il valore
completo, con un tasso di falsi positivi molto superiore.

### Esempi comparativi degli errori PERSON di GLiNER multi

Gli esempi sono tratti dai pattern più frequenti nei falsi positivi di GLiNER
multi. Sullo stesso messaggio WikiNEuRal e Piiranha non producono alcuna
predizione `PERSON` per gli span riportati.

| Messaggio | Span classificato PERSON da GLiNER multi | WikiNEuRal | Piiranha |
| --- | --- | --- | --- | --- |
| `Sono delegato. Ho già provato il recupero, ma nn posso accedere alla vecchia casella email.` | `delegato` | nessuno | nessuno |
| `Sono il responsabile. Ho già provato il recupero, ma nn posso accedere alla vecchia casella email.` | `Sono il responsabile` | nessuno | nessuno |
| `Sono il referente dell'impresa per la Rilevazione annuale della produzione industriale...` | `referente` | nessuno | nessuno |
| `Per inquadrare la richiesta, opera nel ruolo di responsabile o delegato dell'impresa?` | `responsabile` | nessuno | nessuno |
| `...la comunicazione intestata al precedente referente deve essere indirizzata al nuovo referente.` | `precedente referente` | nessuno | nessuno |

Il contrasto è utile anche metodologicamente: GLiNER multi non fallisce perché
non trova le persone — il suo recall `PERSON` è 0,951 — ma perché estende la
categoria a espressioni che denotano ruoli. Piiranha e WikiNEuRal sono più
selettivi in questi esempi, mentre nessuno dei due offre la stessa protezione
degli indirizzi osservata con GLiNER multi.

## Prestazioni

| Modello | Caricamento (s) | Inferenza (s) | Totale (s) | Picco VRAM allocata |
| --- | ---: | ---: | ---: | ---: |
| GLiNER multi | 8,67 | 33,21 | 41,90 | 1,19 GB |
| GLiNER PII | 5,73 | 33,20 | 38,94 | 1,19 GB |
| WikiNEuRal | 0,60 | 16,13 | 16,74 | 0,72 GB |
| Piiranha | 0,74 | 35,38 | 36,12 | 1,14 GB |

## Interpretazione preliminare

L'exact match aggregato non è sufficiente per scegliere il modello operativo.
Piiranha è il riferimento più equilibrato per `PERSON` e `LOCATION`; GLiNER PII
riduce maggiormente l'esposizione residua degli indirizzi, ma produce molte più
predizioni fuori dal gold `PERSON`–`LOCATION`. GLiNER multi offre una copertura
degli indirizzi quasi equivalente con minore espansività di GLiNER PII, pur mantenendo molti
falsi positivi `PERSON`. Il risultato sostiene una pipeline composita in cui
detector diversi sono scelti o riconciliati in base alla categoria e al rischio
operativo. Le conclusioni restano limitate dal carattere sintetico del corpus e
richiedono conferma su un gold umano e, in prospettiva, su dati reali trattati
in ambiente controllato.

### Implicazione architetturale

I risultati non identificano un modello universalmente migliore. Indicano
piuttosto una specializzazione complementare:

- Piiranha è il candidato principale per la baseline NER bilanciata, grazie a
  F1 0,911 su `PERSON`, F1 0,862 su `LOCATION` e nessun falso positivo nelle
  conversazioni negative;
- GLiNER PII è il candidato orientato alla massima copertura degli indirizzi,
  ma la sua elevata espansività ne sconsiglia l'adozione non calibrata;
- GLiNER multi costituisce un compromesso per un ramo indirizzi orientato al
  recall, pur richiedendo una gestione esplicita dei falsi positivi `PERSON`;
- regex e lookup controllati restano responsabili degli identificativi
  strutturati, che non fanno parte di questo confronto NER;
- `merge_detection` dovrà conservare provenienza e sovrapposizioni, senza
  costringere prematuramente detector diversi in un unico span.

Questa evidenza motiva una pipeline composita per categoria e rischio. Non
dimostra ancora che una specifica strategia di merge migliori le metriche
end-to-end: la riconciliazione deve essere implementata e valutata come
esperimento distinto. Analogamente, detection e policy restano problemi
separati: trovare uno span non decide automaticamente se applicare `MASK`,
`KEEP`, `GENERALIZE` o `REVIEW` nel contesto dell'intera conversazione.

In altri termini, i risultati non supportano al momento l'ipotesi di un modello
*one-size-fits-all*. Il modello migliore dipende dall'obiettivo: Piiranha domina
la valutazione exact-match bilanciata, mentre GLiNER PII domina la copertura
degli indirizzi accettando una perdita rilevante di precisione. Questa
conclusione è più informativa di una semplice classifica basata sull'F1
aggregato.

### Cosa possiamo sostenere nello short paper

I risultati supportano le seguenti affermazioni circoscritte:

1. l'exact match aggregato non descrive da solo il rischio residuo associato
   agli indirizzi;
2. sul corpus sintetico proposto, Piiranha offre il miglior equilibrio
   exact-match complessivo, mentre GLiNER PII offre la migliore copertura
   operativa degli indirizzi al costo di molte predizioni fuori dal gold di
   riferimento;
3. la valutazione per componenti rivela differenze che restano nascoste nelle
   sole metriche micro aggregate;
4. una valutazione invariante rispetto alla segmentazione distingue gli errori
   di granularità dalle omissioni che lasciano dati identificativi esposti;
5. la complementarità osservata giustifica lo studio di una pipeline ibrida
   NER–regex con riconciliazione esplicita.

Non possiamo invece concludere che le stesse prestazioni valgano sul traffico
reale, che il corpus rappresenti la prevalenza reale delle categorie, che il
gold sia equivalente a un'annotazione umana o che la pipeline produca già dati
anonimi in senso sostanziale.

### Minacce alla validità

- **Dati sintetici:** lessico, strutture dialogiche e ripetizioni dipendono dai
  template e dal modello generativo.
- **Gold programmatico:** gli offset sono affidabili rispetto agli slot, ma le
  scelte semantiche e i confini delle entità non sono stati validati da più
  annotatori indipendenti.
- **Sovracampionamento degli indirizzi:** utile per lo stress test, ma non
  rappresentativo della frequenza operativa.
- **Dipendenza dai formati locali:** nomi, strade, comuni e codici derivano dai
  cataloghi selezionati per il progetto.
- **Singola configurazione per modello:** non è stata condotta una ricerca
  sistematica delle soglie; in particolare, la precisione di GLiNER potrebbe
  cambiare variando 0,5.
- **Assenza di valutazione end-to-end:** non sono ancora misurate la fusione con
  regex, la policy conversazionale, il masking finale o il rischio residuo
  sull'intera conversazione.
- **Nessun test indipendente reale:** la validazione su conversazioni reali
  richiederà un ambiente controllato, autorizzazioni adeguate e un protocollo
  di annotazione dedicato.

### Sviluppi successivi

Per il prodotto e per un eventuale paper esteso, i passaggi naturali sono:

1. analizzare soglie e calibrazione di GLiNER, in particolare il trade-off fra
   falsi positivi `PERSON` e recall degli indirizzi;
2. introdurre una riconciliazione per categoria fra Piiranha, GLiNER e regex;
3. valutare separatamente forme rare o ambigue di indirizzo e combinazioni di
   quasi-identificatori a livello di conversazione;
4. costruire un piccolo gold umano con linee guida e accordo fra annotatori;
5. mantenere la valutazione a livello di dataset come sviluppo successivo che
   richiederà anche il coinvolgimento del management.

## Artefatti

- Dataset: `output/dataset_detection_paper_300/`
- Configurazione: `config/esperimento_ner_person_location_paper_300.json`
- Predizioni e metriche principali: `output/confronto_ner_person_location_paper_300_run3/`
- Valutazione indirizzi: riproducibile con `src/valuta_indirizzi.py` sulle
  predizioni della `run3`
