# Setup della VM Azure A100

Questa guida prepara un ambiente Python dedicato per il confronto dei modelli
NER sulla Compute Instance Azure A100. I comandi presuppongono che il repository
sia già disponibile sulla VM e che il disco abbia spazio sufficiente per
l'ambiente, le dipendenze CUDA e i pesi dei modelli.

L'esecuzione degli esperimenti resta a cura dell'utente. Non avviare il confronto
prima di avere completato sia la verifica CUDA sia il controllo offline.

## Verifica iniziale della GPU e del disco

Dalla root del repository controllare driver, GPU e memoria video:

```sh
nvidia-smi
```

La VM usata per il primo confronto espone una NVIDIA A100 80 GB PCIe. Il campo
`CUDA Version` mostrato da `nvidia-smi` indica la versione massima supportata dal
driver, non necessariamente un toolkit CUDA installato nel sistema.

Controllare anche lo spazio disponibile sul filesystem root:

```sh
df -h /
```

È opportuno conservare un margine ampio: durante l'installazione e il download
dei modelli possono coesistere temporaneamente pacchetti scaricati, librerie
installate e pesi nella cache.

## Creazione dell'ambiente

La procedura è stata verificata con Python 3.10.12, driver NVIDIA 535.274.02 e
PyTorch 2.6.0 con runtime CUDA 11.8.

```sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

PyTorch viene installato separatamente perché `requirements-modelli.txt`
definisce l'intervallo `torch>=2.6,<3`, ma la build CUDA deve essere scelta in
base al driver della macchina. Per la configurazione verificata:

```sh
python -m pip install --no-cache-dir torch==2.6.0 \
  --index-url https://download.pytorch.org/whl/cu118
```

Verificare che PyTorch usi davvero la GPU:

```sh
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA build:', torch.version.cuda); print('CUDA disponibile:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'nessuna')"
```

Il controllo deve riportare `CUDA disponibile: True` e il nome della A100.
Installare quindi le dipendenze dichiarate dal progetto:

```sh
python -m pip install --no-cache-dir -r requirements-azure.txt
```

L'opzione `--no-cache-dir` evita di conservare nella cache `pip` una seconda
copia dei pacchetti voluminosi. La versione di PyTorch già installata non viene
sostituita perché soddisfa il vincolo del progetto.

## Controllo offline e avvio

Verificare configurazione e dataset senza scaricare pesi o eseguire inferenza:

```sh
python src/confronta_modelli.py --solo-controllo
```

Per il lotto corrente il risultato atteso è di 24 conversazioni e quattro
modelli. Se il controllo passa, avviare il confronto sulla prima GPU:

```sh
python src/confronta_modelli.py \
  --config config/esperimento_modelli.json \
  --device cuda:0
```

I modelli vengono eseguiti in sequenza. Il processo scarica i pesi da Hugging
Face al primo utilizzo e non riprende automaticamente un run interrotto. La
cartella di output configurata deve essere nuova. Per output, codici di uscita e
interpretazione delle metriche vedere [Confronto dei modelli NER](confronto_modelli.md).

## Recupero quando il disco è pieno

Un esperimento precedente può lasciare molti GB nelle cache di `pip` e Hugging
Face. Prima di cancellare file, misurare lo spazio e individuare le directory
più pesanti:

```sh
df -h /
du -h --max-depth=1 /home/azureuser 2>/dev/null | sort -h
du -h --max-depth=2 /home/azureuser/.cache 2>/dev/null | sort -h | tail -n 30
```

### Cache di pip

La cache dei download può essere rimossa senza disinstallare i pacchetti già
presenti negli ambienti:

```sh
python -m pip cache purge
```

I pacchetti rimossi dalla cache dovranno essere riscaricati se serviranno per
una nuova installazione.

### Cache dei modelli Hugging Face

Prima di cancellarla, elencare i repository presenti e le loro dimensioni:

```sh
du -h --max-depth=1 /home/azureuser/.cache/huggingface/hub 2>/dev/null | sort -h
```

Se un singolo modello non serve più, rimuovere soltanto la sua directory
`models--ORGANIZZAZIONE--MODELLO`. Se tutti i pesi presenti appartengono a
esperimenti conclusi e sono riscaricabili, si può eliminare l'intera cache:

```sh
rm -rf /home/azureuser/.cache/huggingface/hub
```

Questo comando elimina i pesi locali, non i repository remoti. Non eseguirlo se
servono repliche offline o se non è stato verificato il contenuto della cache.

### Installazione interrotta

Un errore `No space left on device` può lasciare un virtual environment con
solo una parte delle dipendenze installate. Per un ambiente appena creato e non
ancora usato, la soluzione più affidabile è ricrearlo:

```sh
deactivate
rm -rf /home/azureuser/projects/string-anonym/.venv
python3 -m venv .venv
source .venv/bin/activate
```

Ripetere poi l'aggiornamento di `pip`, l'installazione di PyTorch, la verifica
CUDA e l'installazione di `requirements-azure.txt`. Prima di riprovare,
ricontrollare lo spazio con `df -h /`.
