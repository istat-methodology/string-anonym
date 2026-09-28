# Secondo lotto: copertura mirata del masking

Configurazione: `config/scenari_mirati_v4_2.json`. Prompt 4.2, validazione 3.2.
Il primo catalogo e gli output precedenti restano disponibili. Il nuovo catalogo
contiene 12 varianti con ID distinti, due modalità e un esempio per modalità:
24 schede, 12 positive e 12 negative. Non è una distribuzione rappresentativa
del traffico del servizio e non è un test finale indipendente.

## Copertura richiesta

| Gruppo | Varianti | Entità in ogni scheda positiva | Ripetizioni richieste al chatbot |
|---|---:|---|---|
| Accesso | 4 | COD_UTENTE, PASSWORD | Entrambe, già comunicate dall’utente |
| Pratiche e ricevute | 4 | NUM_PRATICA, PHONE | Entrambe |
| Cambio referente | 2 | PERSON, EMAIL | Entrambe, mantenendo distinte le identità |
| Ricerca territoriale | 2 | ADDRESS, PERSON | ADDRESS, distinto dal territorio della ricerca |

Ogni etichetta prima poco rappresentata (COD_UTENTE, PASSWORD, NUM_PRATICA,
PHONE) è assegnata a quattro conversazioni positive. Le password sono valori
fittizi: la ripetizione è uno stress test del masking, non una buona pratica
raccomandata per il chatbot operativo. Il modello non deve richiederle,
verificarle o suggerire di trasmetterle all’assistenza.

Gli otto casi su accesso/pratiche includono codice e nome PSN. I due casi
territoriali includono comune e anno da conservare, anche nelle modalità
senza entità. Nessun riferimento PSN è forzato nel cambio referente.
Le due forme di richiesta territoriale distinguono residenza e spedizione
personali dal comune oggetto dei dati; non promettono spedizioni.

Le varianti cambiano la situazione iniziale (frammenti, citazioni, confusione
fra codici, richiesta su ricevuta, recapito in firma), senza imporre una
sequenza fissa di turni. L’ambiguità colloquiale del ruolo non è oggetto di
nuovi vincoli. I refusi sono limitati a 1–2 nei messaggi utente, solo negli
stili che li prevedono; il chatbot deve scrivere correttamente.

## Configurazione semplice

- `campionamento_entita: "tutte"` include tutte le entità della variante nelle
  schede positive. Il catalogo precedente continua a usare sottoinsiemi casuali.
- `ripetere_agente` elenca gli slot che il chatbot deve ripetere dopo l’utente.
- `copertura_mirata`, costruita nella scheda, registra slot e riferimenti
  letterali attesi. Nelle schede negative non ci sono slot da ripetere.

La validazione 3.2 segnala in `segnali_copertura` ripetizioni assenti o anticipate
e riferimenti letterali assenti dal dialogo. Queste risposte rimangono salvate,
con gli span, come `da_verificare`. I controlli letterali non dimostrano che il
riferimento sia usato nel significato corretto; la distinzione fra indirizzo e
territorio e l’attribuzione delle identità richiedono lettura dei dialoghi.
Il rispetto dei refusi e la varietà del contenuto restano da revisionare.

## Esecuzione a passi separati

Preparazione locale, senza chiamate API:

```sh
python3 src/genera_prompt.py --catalogo config/scenari_mirati_v4_2.json --per-modalita 1 --seed 0 --output output/prompts_mirati_v4_2.jsonl
```

Dopo aver verificato le schede, il lotto può essere eseguito con
`genera_lotto.py`, specificando `--input output/prompts_mirati_v4_2.jsonl` e
`--cartella-output output/lotto_openai_mirato_v4_2`. Richiede 24 nuove chiamate
in assenza di risultati compatibili. Il controllo preventivo `--solo-controllo`
non effettua chiamate. Gli output storici non vengono riutilizzati perché ID,
schede e istruzioni sono diversi. L’esecuzione delle API resta a cura dell’utente.
