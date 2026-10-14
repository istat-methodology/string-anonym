# Metodologia e pipeline sperimentale

## Separazione fra detection e policy

L'architettura distingue due problemi che nella prima versione del progetto
erano parzialmente sovrapposti:

1. **Detection:** individuare span e categorie nel testo originale di ogni
   messaggio. Regex e NER operano indipendentemente e producono detection con
   provenienza esplicita.
2. **Policy di conversazione:** valutare le detection nel contesto dell'intera
   chat e decidere `MASK`, `KEEP`, `GENERALIZE` o `REVIEW`.

Una futura valutazione complessiva del rischio potrà operare sull'intera
conversazione e, successivamente, sul dataset. Questi livelli non fanno parte
dell'esperimento corrente. Lo short paper misura la detection a livello di
messaggio; non misura anonimizzazione sostanziale o masking end-to-end.

## Domanda sperimentale

La domanda primaria è quanto bene modelli pretrained generalisti e orientati
alle PII riconoscano `PERSON` e `LOCATION` in conversazioni istituzionali
sintetiche, a parità di input e senza fine-tuning sul corpus.

Gli identificativi strutturati — per esempio telefono, codice indagine, numero
pratica e password — appartengono al ramo regex o a lookup controllati. Non
devono abbassare artificialmente le metriche della componente NER. La futura
fase `merge_detection` unirà risultati coincidenti e conserverà overlap,
conflitti e provenienza.

## Gold multilivello

Il gold canonico ammette annotazioni sovrapposte. Un indirizzo completo resta
una detection `ADDRESS`; nella vista NER, la parte stradale con eventuale civico
e il comune sono rappresentati come `LOCATION` distinte quando presenti.

Questa scelta nasce da un limite emerso nella baseline: un gold che impone un
unico span `ADDRESS` considera falsi positivi una strada e un comune
correttamente individuati separatamente. Il gold multilivello non è stato
introdotto per favorire uno specifico modello, ma per distinguere la forma
dell'output dal rischio operativo di lasciare visibile una componente
identificativa.

Per il corpus paper le componenti degli indirizzi sono prodotte durante la
generazione e non inferite a posteriori con euristiche. L'esportatore conserva
anche il gold canonico completo, così le diverse viste restano verificabili.

## Protocollo di esecuzione

I quattro modelli ricevono gli stessi messaggi, uno alla volta. Non ricevono
prompt generativi, gold, metadati descrittivi, turni futuri o ipotesi di policy.
Gli output nativi sono normalizzati in un formato comune senza confrontare gli
score fra modelli. Spazi esterni vengono rimossi dagli offset; overlap e
predizioni ignorate restano registrati.

I modelli sono caricati ed eseguiti in sequenza sulla stessa GPU. La run salva:

- configurazione effettiva e revisioni risolte dei pesi;
- hash degli input e del gold;
- output nativi e predizioni normalizzate;
- metriche, errori per record, tempi e picchi di memoria;
- fallimenti tecnici, separati dalle metriche.

Nella `run3`, assunta come esperimento principale definitivo, tutti e quattro i
modelli hanno elaborato 289/289 conversazioni senza fallimenti tecnici. Le run
precedenti sono conservate per audit: la `run1` documenta il mapping iniziale
incompleto degli indirizzi, mentre la `run2` costituisce un'ablazione in cui
l'etichetta testuale `address` era applicata a GLiNER multi.

## Metriche NER

La baseline usa precision, recall e F1 micro con exact match di categoria,
messaggio e confini dello span. Le metriche vengono riportate globalmente, per
`PERSON` e `LOCATION`, e per ruolo del messaggio. Sono inoltre conservati falsi
positivi, falsi negativi, copertura dei caratteri e risultati sulle
conversazioni negative.

L'exact match è rigoroso e confrontabile, ma non distingue uno span quasi
coincidente che copre il dato da una mancata detection che lo lascia interamente
visibile. Per questa ragione non viene interpretato come unica misura del
rischio residuo.

## Valutazione operativa degli indirizzi

Dopo aver congelato le predizioni e le metriche exact-match, una seconda analisi
misura la copertura degli indirizzi senza modificare gli output dei modelli.
Per ogni occorrenza vengono calcolati:

- copertura completa dell'indirizzo;
- quota di caratteri alfanumerici coperti;
- copertura di strada, civico, interno e comune;
- testo residuo che resterebbe visibile;
- tassonomia dell'esito, per esempio `complete`, `house_number_exposed`,
  `municipality_only` o `uncovered`.

La copertura è l'unione degli span `LOCATION` predetti. Un indirizzo può quindi
essere protetto da più span separati, per esempio strada e comune. Questa
analisi è complementare all'exact match e risponde a una domanda diversa:
quanto contenuto identificativo rimarrebbe esposto se le detection fossero
utilizzate per il masking?

Questa misura può essere interpretata come **copertura dell'indirizzo invariante
rispetto alla segmentazione**. Considera operativamente equivalenti una
predizione unica, per esempio `Via Nome 12, Comune`, e due predizioni separate,
`Via Nome 12` e `Comune`, quando la loro unione copre gli stessi caratteri
sensibili. Non sostituisce l'exact match standard e non modifica il gold: rende
visibile quanto degli errori di confine derivi dalla diversa granularità degli
span anziché da una mancata detection.

## Interpretazione e confini delle conclusioni

Il confronto è diagnostico e orientato alla progettazione della pipeline. Non
dimostra ancora che una specifica strategia di merge migliori l'anonimizzazione
finale. Detection e policy rimangono separate: il riconoscimento di uno span non
determina automaticamente la decisione contestuale da applicare.

La valutazione a livello di intera conversazione è prevista come fase futura;
quella sull'intero dataset richiede anche un coinvolgimento organizzativo e
rimane fuori dal perimetro corrente.

## Incertezza mediante bootstrap

Le predizioni congelate della `run3` sono analizzate con un bootstrap appaiato
per conversazione. Ogni replica campiona con reinserimento 289 conversazioni e
usa lo stesso campione per tutti i modelli. Sono eseguite 10.000 repliche con
seed fisso `20261014`; vengono riportati intervalli percentile al 95%, media,
bias, varianza ed errore standard bootstrap.

Il cluster è l'intera conversazione, non il singolo span o indirizzo: in questo
modo turni, entità e ripetizioni correlate restano insieme. Il disegno appaiato
permette inoltre di stimare direttamente l'intervallo della differenza fra due
modelli. Gli intervalli descrivono la variabilità condizionata al corpus
sintetico e non la generalizzazione al traffico reale.

## Artefatti riproducibili

- Configurazione: `config/esperimento_ner_person_location_paper_300.json`
- Runner: `src/confronta_modelli.py`
- Valutazione indirizzi: `src/valuta_indirizzi.py`
- Bootstrap: `src/bootstrap_metriche.py`
- Output principale: `output/confronto_ner_person_location_paper_300_run3/`
- Output bootstrap: `output/bootstrap_ner_person_location_paper_300_run3/`

