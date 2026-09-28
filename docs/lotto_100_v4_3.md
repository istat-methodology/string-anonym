# Lotto OpenAI da 100 conversazioni

Prompt 4.3, catalogo mirato 4.3, seed 100. Le 12 varianti ricevono
4 esempi per modalità; le prime due (accesso/tentativi e accesso/citazione)
ne ricevono 5. Totale: 50 con dati personali e 50 senza.
È un lotto di sviluppo mirato, non una distribuzione rappresentativa del
contact centre né un insieme indipendente per la valutazione finale.

Eseguire dalla root del progetto, un passo alla volta.

1. Preparazione locale, senza API:
   `.venv/bin/python src/lotto.py prepara --config config/lotto_100_v4_3.json`
2. Controllo del piano, senza API:
   `.venv/bin/python src/lotto.py controlla --config config/lotto_100_v4_3.json`
3. Generazione (100 chiamate OpenAI se nessuna risposta è riutilizzabile):
   `.venv/bin/python src/lotto.py genera --config config/lotto_100_v4_3.json`

Le schede sono in `output/prompts_100_v4_3.jsonl`; le risposte e il piano
sono in `output/lotto_openai_100_v4_3/`, con risultato `chat_lotto.jsonl`.
Gli script rifiutano di sovrascrivere gli output. In caso di interruzione
conservare la cartella e verificare gli esiti prima di procedere; non è
prevista una ripresa automatica. L'esecuzione resta a cura dell'utente.

Questo lotto è già stato eseguito: la configurazione ne conserva la ricetta,
non va rilanciata per correggere gli scarti. Per un nuovo esperimento copiare
la configurazione e scegliere nuovi percorsi di output e un seed appropriato.
I percorsi interni alla configurazione sono relativi alla root del progetto.
Il comando comune usa gli stessi generatori esistenti; non contiene una
seconda implementazione della pipeline. Non inserire chiavi API nel JSON.

Se la cartella di output esiste, `controlla` legge il risultato finale e
mostra risposte presenti, valide, da verificare ed errori API. Controlla che
ID, prompt, provider e deployment corrispondano al lotto richiesto. Una
cartella senza risultato finale o un lotto parziale sono segnalati per
verifica, senza proporre nuove chiamate o avviare una ripresa automatica.
Il riepilogo riporta gli stati salvati, senza rivalidare le risposte.

`valido` indica il superamento dei controlli implementati: la revisione
dei dialoghi deve ancora valutare promesse operative, naturalezza e coerenza.
