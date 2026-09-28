# Step 2: valutatore del masking

`src/valuta_masking.py` non utilizza modelli né API. Riceve input, annotazioni
attese e predizioni in tre file JSONL separati. I primi due sono prodotti dallo
step 1. Le predizioni saranno prodotte dal componente di riconoscimento.

Ogni riga delle predizioni contiene `id`, `stato: "ok"` e `annotazioni`.
Ogni annotazione contiene `campo` (es. `conversazione.0.testo`), `start`, `end`
e `tipo`; `testo` è facoltativo, ma se presente deve coincidere con lo span.
Gli offset sono Unicode Python, con fine esclusa. Gli span devono essere
non sovrapposti: il formato rappresenta la decisione finale, non i candidati.
Un esito senza entità è `stato: "ok", annotazioni: []`.
Un fallimento è `stato: "errore", errore: "descrizione"`, senza annotazioni.

ID mancanti nelle predizioni e fallimenti sono riportati separatamente, non
interpretati come assenza di entità. Le metriche riguardano solo gli esiti ok:
leggere sempre anche la copertura delle conversazioni e il numero di fallimenti.
ID estranei o duplicati e span malformati bloccano la valutazione.

Il report include precision/recall/F1 sugli span esatti con tipo, per categoria
e ruolo, copertura dei caratteri sensibili indipendente dal tipo, caratteri
non sensibili mascherati e negativi con falsi positivi. I rapporti senza
denominatore sono `null`, non 1. Una categoria errata con confini corretti
produce FP e FN nella metrica esatta, ma copertura dei caratteri completa.
Gli errori elencati usano tuple [indice messaggio, start, end, tipo].

Non valuta ancora associazione alle identità, testo sostituito, latenza o
memoria. Non approva le annotazioni attese: quelle esportate restano un
riferimento di sviluppo non revisionato. Non misura qualità semantica generale.

Prima verifica, con esempi artificiali ed errori intenzionali:

```sh
.venv/bin/python tests/test_valuta_masking.py
```

Questa prova controlla i calcoli, non le prestazioni di un modello. Quando
saranno disponibili predizioni vere, il comando riutilizzabile sarà:

```sh
.venv/bin/python src/valuta_masking.py \
  --input output/dataset_masking_v4_4/input.jsonl \
  --attese output/dataset_masking_v4_4/annotazioni_attese.jsonl \
  --predizioni PERCORSO_PREDIZIONI.jsonl \
  --output PERCORSO_REPORT_NUOVO.json
```

Il report non sovrascrive file esistenti e registra percorsi e hash delle fonti.
