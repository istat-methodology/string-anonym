# Pulizia prima della commit

Verifica del 28 settembre 2026. Nessun file cancellato.

## Conservare nella commit

Codice attuale, test, requirements, README, specifica, configurazioni e
documentazione, incluso metodologia_masking.md e .env.example con chiavi vuote.
Conservare src/original come riferimento storico e i dati locali necessari
alla generazione. src/jsonl2json.py è un'utilità riutilizzabile, non un output.

Conservare i cataloghi 4.2 e 4.3: sono piccoli, documentano gli esperimenti
e tests/test_lotto_mirato.py usa ancora quello 4.2. Non eliminarli isolatamente.
Conservare PDF e documenti sorgente per la provenienza delle specifiche.

## Conservare fuori dalla commit

output/ è esclusa da Git. Non è un backup: prima di eliminarla archiviarla
altrove. Conservare in particolare tutti i lotti completi (chat_lotto.jsonl,
piano, risposte nuove/riusate) e i prompt associati. La revisione del lotto 100
fa riferimento all'hash dell'originale: non modificarlo.

.env contiene la configurazione locale e deve restare escluso. .venv è
l'ambiente locale: non versionarlo e non serve rimuoverlo per fare pulizia.

## Eliminabili

- .DS_Store, __pycache__/ e *.pyc: cache rigenerabili, già ignorate.
- scripts/: cartella vuota dopo la sostituzione dei due wrapper; Git non
  versiona cartelle vuote.
- docs/dataset_conll_advanced.txt: copia byte per byte identica a
  src/original/dataset_conll_advanced.txt (hash verificato). Tenere quella in
  src/original; non risultano riferimenti alla copia docs nei file verificati.

I vecchi output/test_* e prompt delle prove isolate possono essere archiviati
fuori dalla cartella di lavoro. Eliminarli perde la traccia di quei test e
potenziali fonti di riuso: non sono semplici cache. Le esportazioni .json
possono essere ricreate dai rispettivi .jsonl se contengono gli stessi record.

## Commit

La pulizia del disco non è necessaria per la commit: output, ambiente e
credenziali sono ignorati. Controllare git diff e git status, includere i nuovi
file di codice/configurazione/documentazione, poi effettuare la commit.
Questa commit può fissare la pipeline sintetica consolidata e la proposta
metodologica; implementazione e training del masking partiranno dopo.
