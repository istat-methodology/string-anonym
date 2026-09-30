# Confronto dei modelli NER

Lo script `src/confronta_modelli.py` legge `config/esperimento_modelli.json`,
esegue i modelli in sequenza sullo stesso input e applica il valutatore esistente.
Questo primo esperimento usa messaggi isolati: ciascun modello riceve soltanto
il testo del messaggio corrente, senza annotazioni attese, riepiloghi o turni
successivi. Non esegue fine-tuning, combinazioni con regex o sostituzioni nel testo.

## Modelli e conversione delle categorie

| Modello | Funzione nel confronto | Licenza dichiarata dei pesi |
|---|---|---|
| [GLiNER multilingual](https://huggingface.co/urchade/gliner_multi-v2.1) | Riconoscimento con categorie richieste a runtime | Apache-2.0 |
| [GLiNER multilingual PII](https://huggingface.co/urchade/gliner_multi_pii-v1) | Variante specializzata nei dati identificativi | Apache-2.0 |
| [WikiNEuRal](https://huggingface.co/Babelscape/wikineural-multilingual-ner) | Baseline NER multilingue a categorie fisse | CC-BY-NC-SA-4.0 |
| [Piiranha](https://huggingface.co/iiiorg/piiranha-v1-detect-personal-information) | Riconoscimento PII a categorie fisse | CC-BY-NC-ND-4.0 |

La configurazione v2 aggiunge due candidati Apache-2.0: GLiNER2 PII
multilingue, specializzato su 42 tipi di informazioni identificative, e
GLiNER2.5 Multi, generalista multilingue con architettura boundary. Il backend
GLiNER2 usa gli offset restituiti dalla libreria e conserva l'output convertito
nel formato nativo del runner. NuNER Zero non è incluso in questa fase perché la
model card lo presenta come modello inglese; potrà essere provato separatamente
senza confondere il confronto principale in italiano.

La disponibilità dei pesi non implica libertà di impiego o modifica per ogni
scopo. Le licenze dei due ultimi modelli richiedono una verifica distinta prima
di impieghi ulteriori rispetto al confronto di ricerca.

La configurazione definisce per ogni modello repository, revisione, backend,
soglia, limite di token, mappatura delle etichette e categorie da aggregare.
Per aggiungere o rimuovere un modello dei backend supportati basta modificare
la lista `modelli`. I percorsi dei dati sono relativi alla root del progetto.

Per GLiNER le chiavi di `etichette` sono le descrizioni richieste al modello.
Per gli altri modelli sono le categorie native; il valore è la categoria del
nostro benchmark. `null` significa esclusione esplicita, registrata negli output.
WikiNEuRal contribuisce soltanto a PERSON: LOC non equivale a un indirizzo
personale e ORG non è una delle sette categorie attuali.
Piiranha mappa nomi e cognomi a PERSON e strada, civico e CAP ad ADDRESS;
CITY è esclusa perché una città isolata non identifica necessariamente l’utente.
Questa scelta può produrre indirizzi incompleti: è un limite da misurare,
non una soluzione completa del riconoscimento degli indirizzi.
ACCOUNTNUM non viene convertito in NUM_PRATICA.

Per Piiranha, segmenti adiacenti della stessa categoria PERSON o ADDRESS,
separati soltanto da spazi o virgole, vengono uniti. È un’euristica esplicita,
che può sbagliare; le predizioni native restano disponibili per l’analisi.
Gli spazi esterni inclusi negli offset dal tokenizer vengono rimossi prima della
valutazione; gli output nativi conservano gli offset originali. La punteggiatura
non viene rimossa automaticamente.
I conflitti fra span dello stesso modello sono risolti per score, poi lunghezza.
Non confrontiamo gli score fra modelli diversi.

## Esecuzione, un passo alla volta

Primo controllo, senza rete, pesi o dipendenze ML:

```sh
.venv/bin/python src/confronta_modelli.py --solo-controllo
```

Verifica configurazione e dataset. Non crea output. Il lotto corrente di 24
conversazioni serve come prova di funzionamento, non come test finale del paper.

Sulla macchina di ricerca con GPU, predisporre un ambiente Python dedicato e
PyTorch compatibile con il CUDA disponibile. Il file `requirements-azure.txt` include le dipendenze di generazione e quelle
di `requirements-modelli.txt`, senza duplicarne gli elenchi; GLiNER è fissato alla versione 0.2.21, di cui abbiamo
verificato l’interfaccia di preprocessing. Nel relativo ambiente:

```sh
python -m pip install -r requirements-azure.txt
```

L’esecuzione effettiva scarica i pesi da Hugging Face e usa la GPU indicata:

```sh
python src/confronta_modelli.py --config config/esperimento_modelli.json --device cuda:0
```

Se CUDA non è disponibile viene segnalato un errore, senza passaggio automatico
alla CPU. Il default è `cpu` se si omette `--device`. Il percorso `output` deve
essere nuovo: per ripetere l’esperimento modificarlo nella configurazione.
I modelli vengono caricati uno alla volta; non c’è ripresa automatica dei run.

## Output e interpretazione

La cartella dell’esperimento contiene la configurazione utilizzata, un manifest
con hash dei dati e versioni delle librerie, e `riepilogo.json` con stato e
metriche di ciascun modello. Il riepilogo e i manifest dei modelli registrano
anche durata di caricamento, durata di inferenza, durata totale e, su CUDA, i
picchi di memoria allocata e riservata osservati da PyTorch. Queste misure sono
utili per confrontare GPU diverse, ma includono rumore di sistema e vanno
raccolte a parità di configurazione e stato della cache. Ogni sottocartella contiene:

- `predizioni.jsonl`: span convertiti nel formato comune o errori espliciti;
- `predizioni_native.jsonl`: etichette originali e offset per ogni messaggio;
- `valutazione.json`: metriche e dettaglio degli errori rispetto alle attese;
- `manifest.json`: configurazione del modello, revisione risolta ed eventuali errori.

Se un modello non si carica, il ciclo continua con il successivo e conserva
l’errore nel manifest. Se fallisce un messaggio, la conversazione intera viene
segnalata come errore, senza valutare predizioni parziali. I messaggi oltre il
limite vengono segnalati, non troncati silenziosamente. Non c’è ancora una
strategia a finestre per testi lunghi. Gli errori tecnici sono esclusi dalle
metriche e contati separatamente: confrontare sempre anche il numero di
conversazioni valutate. Un run parziale o fallito termina con codice diverso da zero.

Il riepilogo misura il compito completo sulle sette categorie. Non è una
classifica della sola qualità NER: WikiNEuRal non copre sei categorie e Piiranha
non copre NUM_PRATICA. Consultare le metriche per categoria e i falsi positivi,
oltre ai risultati globali. Un nome correttamente riconosciuto può comunque
essere un riferimento pubblico da conservare: la decisione contestuale resta
parte del problema di ricerca.

Le revisioni dei repository principali vengono risolte e registrate come hash.
Per repliche successive sostituire `main` con gli hash registrati. Le dipendenze
esterne caricate dai modelli, l’ambiente CUDA e le versioni delle librerie devono
essere conservati separatamente per una replica completa.

I test locali coprono orchestrazione, conversione degli span, errori e valutazione
con backend simulati. L’inferenza reale e la compatibilità dell’intero ambiente
verranno verificate con il primo run sulla macchina di ricerca.
