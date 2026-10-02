# Prompt separati per chat e policy

## Prompt chat 5.0

`src/genera_prompt.py` costruisce schede con entità a segnaposto e riferimenti
pubblici controllati. Il modello restituisce soltanto metadati e conversazione.
Non vede le ipotesi di policy e non produce annotazioni.

Dalla versione `5.0-draft4` ogni conversazione deve contenere almeno tre scambi
completi, cioè almeno sei messaggi non vuoti, e deve terminare con una risposta
sostanziale dell'Agente. `numero_scambi` resta l'obiettivo superiore: è possibile
fermarsi prima solo dopo il minimo, se proseguire richiederebbe contenuti
artificiali. Il vincolo serve a produrre contesto sufficiente per gli esperimenti
di policy.

Dopo la risposta, `src/validazione.py` inserisce i valori sintetici e produce
`detection_attesa` sul testo originale. Gli offset sono Unicode, con fine esclusa.

## Policy contestuale di conversazione

`src/genera_prompt_policy.py` legge le chat 5.0 validate e costruisce un secondo
prompt. Il modello riceve conversazione completa, detection e versione della
policy; restituisce una decisione per ogni `detection_id`. L'intera conversazione
serve da contesto per le decisioni puntuali, ma non viene ancora prodotto un
giudizio aggregato sul rischio residuo.

Le azioni sono `KEEP`, `MASK`, `GENERALIZE` e `REVIEW`. Le ipotesi attese sono
salvate in `attese_policy`, fuori dai messaggi inviati al modello. Ogni ipotesi
ha stato:

- `APPROVED`: convenzione già concordata;
- `PROVISIONAL`: ipotesi di lavoro valutabile separatamente;
- `OPEN`: decisione da discutere, esclusa dal gold definitivo.

`MASK` usa soltanto placeholder neutri coerenti con il tipo, come `[PERSON_1]`;
`GENERALIZE` usa invece una formulazione che conserva il ruolo contestuale, come
«la società acquirente». Le ripetizioni dello stesso elemento devono mantenere
lo stesso replacement.

La configurazione corrente è `config/policy_conversation_draft_2.json`. La
valutazione aggregata del rischio residuo della conversazione è rinviata a un
esperimento successivo e avrà un contratto separato. Cambiare policy non richiede
di rigenerare automaticamente le conversazioni.

Il runner `src/genera_policy.py` usa gli stessi provider Foundry della generazione
chat, salva progressivamente la risposta originale e accetta come valido soltanto
un output con una decisione per ogni `detection_id`.

## Limiti correnti

Non sono ancora presenti il valutatore quantitativo della policy e il sostitutore
finale. La valutazione complessiva del rischio residuo della conversazione non è
implementata e non va confusa con la policy contestuale per singola detection.
Dati sanitari e rischio a livello dataset sono fuori perimetro. L'esito del
prompt non certifica l'anonimizzazione.
