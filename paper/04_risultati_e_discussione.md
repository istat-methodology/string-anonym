# Risultati detection sul corpus paper — run 1

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
fine-tuning sul corpus. GLiNER riceve le etichette testuali `person` e
`location`; WikiNEuRal e Piiranha usano le rispettive mappature native. Le
soglie non sono state ottimizzate sui 289 esempi: per GLiNER è usata 0,5,
mentre per i modelli token-classification è mantenuto il comportamento nativo.

## Exact match

| Modello | Precision | Recall | F1 | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GLiNER multi | 0,465 | **0,924** | 0,619 | 387 | 445 | 32 |
| GLiNER PII | 0,221 | 0,480 | 0,303 | 201 | 708 | 218 |
| WikiNEuRal | 0,633 | 0,666 | 0,649 | 279 | 162 | 140 |
| Piiranha | **0,946** | 0,666 | **0,782** | 279 | 16 | 140 |

### Metriche per categoria

| Modello | PERSON P | PERSON R | PERSON F1 | LOCATION P | LOCATION R | LOCATION F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GLiNER multi | 0,251 | **0,951** | 0,397 | 0,740 | **0,912** | **0,817** |
| GLiNER PII | 0,198 | 0,967 | 0,329 | 0,266 | 0,277 | 0,272 |
| WikiNEuRal | 0,719 | 0,813 | 0,763 | 0,593 | 0,605 | 0,599 |
| Piiranha | **0,904** | 0,919 | **0,911** | **0,976** | 0,561 | 0,712 |

Piiranha ottiene il miglior exact-match complessivo e su `PERSON`. GLiNER multi
ha invece il recall più elevato e il miglior F1 su `LOCATION`. La bassa
precisione `PERSON` di GLiNER multi è concentrata soprattutto su termini di
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
GLiNER multi privilegia il recall e produce molti falsi positivi `PERSON`;
Piiranha è molto più selettivo e ottiene una precisione elevata. La scelta tra i
due non può essere derivata dal solo F1 micro quando il costo di una mancata
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

| Modello | Indirizzi completi | Tasso completo | Copertura caratteri | Esposizione residua |
| --- | ---: | ---: | ---: | ---: |
| GLiNER multi | **120/124** | **0,968** | **0,983** | **0,017** |
| GLiNER PII | 50/124 | 0,403 | 0,436 | 0,564 |
| WikiNEuRal | 16/124 | 0,129 | 0,792 | 0,208 |
| Piiranha | 0/124 | 0,000 | 0,272 | 0,728 |

### Copertura completa per variante

| Variante | N | GLiNER multi | GLiNER PII | WikiNEuRal | Piiranha |
| --- | ---: | ---: | ---: | ---: | ---: |
| Completo standard | 34 | **34** | 6 | 2 | 0 |
| Civico complesso | 18 | **18** | 3 | 0 | 0 |
| Con interno/scala | 17 | **17** | 4 | 0 | 0 |
| Senza civico | 15 | **14** | 13 | 12 | 0 |
| Senza comune | 22 | **22** | 11 | 1 | 0 |
| Senza tipo di strada | 18 | **15** | 13 | 1 | 0 |

GLiNER multi copre inoltre completamente 121/124 componenti stradali, 107/110
civici, 17/17 interni e 105/105 comuni. I quattro casi non completi sono tre
occorrenze senza tipo di strada e una senza civico. WikiNEuRal lascia spesso
esposto il numero civico; Piiranha riconosce prevalentemente il comune e non
copre mai l'indirizzo completo.

### Interpretazione degli indirizzi

Il risultato sul campione ampio conferma quanto era emerso nell'ispezione
qualitativa della baseline: GLiNER multi spesso segmenta l'indirizzo in modo
più utile rispetto al gold legacy, individuando separatamente strada e comune.
La revisione del gold non è stata introdotta per “salvare” il modello, ma per
allineare la valutazione al rischio osservabile: ciò che conta ai fini della
protezione è quanta parte dell'indirizzo rimane esposta.

La conferma sulle sei varianti riduce il rischio che il risultato dipenda solo
dal formato standard `Via Nome 12, Comune`. GLiNER multi copre integralmente
tutti gli indirizzi con civico complesso e tutti quelli con interno o scala; i
quattro casi incompleti si concentrano nelle forme senza tipo di strada o senza
civico. Queste forme restano quindi casi di attenzione per test futuri.

| Caso non completamente coperto da GLiNER multi | Esito | Testo residuo |
| --- | --- | --- |
| `Giovanni Agnelli 185, Minturno` | solo comune | `Giovanni Agnelli 185` |
| `Della Faterna 248, Poli` — messaggio utente | civico esposto | `248` |
| `Della Faterna 248, Poli` — ripetizione Agente | solo comune | `Della Faterna 248` |
| `Via Giuseppe Garibaldi, Ferentino` | solo comune | `Via Giuseppe Garibaldi` |

WikiNEuRal raggiunge una copertura media dei caratteri relativamente alta ma
solo 16 indirizzi completamente coperti: la differenza è dovuta soprattutto a
civici e interni lasciati visibili. Piiranha ottiene invece un buon exact match
su molte `LOCATION` che corrispondono ai comuni, ma questo non si traduce nella
protezione dell'indirizzo completo. Il risultato mostra concretamente perché
il conteggio di entità corrette e la copertura del dato sensibile rispondono a
domande diverse.

### Esempi comparativi sugli indirizzi

Gli esempi seguenti includono una forma per ciascuna variante del piano. Sono
stati selezionati fra i casi in cui GLiNER multi copre il 100% dell'indirizzo e
WikiNEuRal non lo copre integralmente. La colonna “residuo” riporta i caratteri
alfanumerici che rimarrebbero visibili secondo la valutazione operativa; non è
una ricostruzione manuale delle predizioni.

| Variante ed esempio | GLiNER multi | WikiNEuRal | Piiranha |
| --- | --- | --- | --- |
| Completo: `Via Casal Di Zaino 109, Cisterna di Latina` | **100%**, nessun residuo | 91,2%, residuo `109` | 47,1%, residuo `Via Casal Di Zaino 109` |
| Senza tipo di strada: `Giovanni Agnelli 185, Minturno` | **100%**, nessun residuo | 30,8%, residuo `Giovanni Agnelli 185` | 30,8%, residuo `Giovanni Agnelli 185` |
| Senza civico: `Traversa Prima Vigne Inferiori, Santi Cosma e Damiano` | **100%**, nessun residuo | 40,0%, residuo `Traversa Prima Vigne Inferiori` | 40,0%, residuo `Traversa Prima Vigne Inferiori` |
| Senza comune: `Via Colle Sant'Upica 28` | **100%**, nessun residuo | 89,5%, residuo `28` | 0%, indirizzo interamente esposto |
| Civico complesso: `Via Silvio Pellico 198 bis, Antrodoco` | **100%**, nessun residuo | 80,6%, residuo `198 bis` | 29,0%, residuo `Via Silvio Pellico 198 bis` |
| Con interno: `Via La Foresta 169, interno 7, Anagni` | **100%**, nessun residuo | 62,1%, residuo `169, interno 7` | 20,7%, residuo `Via La Foresta 169, interno 7` |

Questi casi chiariscono il diverso comportamento dei modelli. WikiNEuRal
riconosce spesso strada e comune ma esclude il civico o l'interno dal confine
dello span. Piiranha tende a riconoscere il comune, che è una `LOCATION`
corretta in exact match, lasciando però visibile la parte più identificativa
dell'indirizzo. GLiNER multi include invece le componenti in uno o più span la
cui unione copre il valore completo.

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
| GLiNER multi | 30,91 | 34,54 | 65,46 | 1,19 GB |
| GLiNER PII | 12,05 | 31,22 | 43,29 | 1,19 GB |
| WikiNEuRal | 6,54 | 15,62 | 22,17 | 0,72 GB |
| Piiranha | 9,52 | 33,03 | 42,55 | 1,14 GB |

## Interpretazione preliminare

L'exact match aggregato non è sufficiente per scegliere il modello operativo.
Piiranha è il riferimento per `PERSON`, mentre GLiNER multi è nettamente il
modello più efficace per ridurre l'esposizione residua degli indirizzi. Il
risultato sostiene una pipeline composita in cui detector diversi sono scelti
o riconciliati in base alla categoria e al rischio operativo. Le conclusioni
restano limitate dal carattere sintetico del corpus e richiedono conferma su un
gold umano e, in prospettiva, su dati reali trattati in ambiente controllato.

### Implicazione architetturale

I risultati non identificano un modello universalmente migliore. Indicano
piuttosto una specializzazione complementare:

- Piiranha è il candidato principale per `PERSON`, grazie a F1 0,911 e a soli
  12 falsi positivi;
- GLiNER multi è il candidato principale per gli indirizzi e per un ramo
  `LOCATION` orientato al recall;
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
*one-size-fits-all*. Il modello migliore dipende dalla categoria e dalla
metrica operativa: Piiranha domina su `PERSON`, mentre GLiNER multi domina sulla
copertura degli indirizzi. Questa conclusione è più informativa di una semplice
classifica basata sull'F1 aggregato.

### Cosa possiamo sostenere nello short paper

I risultati supportano le seguenti affermazioni circoscritte:

1. l'exact match aggregato non descrive da solo il rischio residuo associato
   agli indirizzi;
2. sul corpus sintetico proposto, GLiNER multi offre la migliore copertura
   operativa degli indirizzi, mentre Piiranha offre il miglior riconoscimento
   exact-match delle persone;
3. la valutazione per componenti rivela differenze che restano nascoste nelle
   sole metriche micro aggregate;
4. la complementarità osservata giustifica lo studio di una pipeline ibrida
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
- Predizioni e metriche: `output/confronto_ner_person_location_paper_300_run1/`
- Valutazioni indirizzi: file `valutazione_indirizzi.json` nella cartella di ciascun modello
