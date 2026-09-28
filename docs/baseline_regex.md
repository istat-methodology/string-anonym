# Step 3: baseline a regole

`src/predici_regex.py` legge soltanto input.jsonl. Non legge annotazioni attese,
schede o generatori di valori; non usa modelli né API. Produce una nuova cartella
con predizioni.jsonl (compatibile col valutatore) e manifest.json con hash delle
fonti e versione delle regole. Gli originali non vengono modificati.

Le regex sono modificabili in config/regole_masking.json. Ogni regola specifica
nome, tipo, priorità e pattern con gruppo `valore`: solo quel gruppo diventa span.
I conflitti privilegiano priorità maggiore, poi span più lungo, posizione e nome.
Sono decisioni iniziali da misurare, non priorità valide per ogni contesto.

Copertura iniziale: email, cellulari italiani di dieci cifre con eventuale +39,
spazi o punti, protocolli/pratiche numerici introdotti da parole esplicite,
codici P0/QOL e codici numerici introdotti come codice utente; password esplicite
di almeno sei caratteri con lettere e almeno una cifra o un simbolo supportato.
La password non richiede due punti. PASSWORD non copre ogni forma possibile:
valori solo alfabetici, solo numerici o simboli non previsti possono sfuggire.

Limiti dichiarati:
- Nessun riconoscimento di PERSON e ADDRESS.
- Nessuna propagazione fra turni: si elaborano entrambi i ruoli, ma ogni messaggio
  è indipendente. Ripetizioni senza indizi locali possono sfuggire.
- Telefoni fissi/internazionali e codici in formati diversi non sono coperti.
- Email e formati telefonici sono mascherati senza distinguere contatti pubblici:
  servono negativi difficili per misurare questi falsi positivi.
- Un numero statistico simile a un cellulare può generare un falso positivo.
- Non è ancora il sistema contestuale né il componente di sostituzione.

Le regole sono state definite sulla conoscenza dei formati di sviluppo, prima
della misurazione. Le prestazioni sui lotti già usati per progettare il sistema
non sono una stima indipendente di generalizzazione.

Primo comando (nessuna GPU o API):

```sh
.venv/bin/python src/predici_regex.py \
  --input output/dataset_masking_v4_4/input.jsonl \
  --output output/predizioni_regex_v1_v4_4
```

Successivamente si passa predizioni.jsonl al valutatore dello step 2. Un esito
`ok` indica esecuzione riuscita, non riconoscimento corretto. Gli errori per
conversazione sono salvati esplicitamente e producono un codice di uscita non
zero; nessuna predizione parziale viene presentata come riuscita.
