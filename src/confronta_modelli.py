"""Esperimento sequenziale di modelli NER: controllo offline o inferenza e valutazione."""
import argparse
from collections import Counter
import gc
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import time

from esporta_dataset_masking import leggi, TIPI
from valuta_masking import span_validi, valuta

ROOT = Path(__file__).resolve().parents[1]


def salva(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def carica(path):
    cfg = json.loads(path.read_text(encoding='utf-8'))
    if cfg['contesto'] != 'messaggio_isolato':
        raise ValueError('Questa versione supporta solo messaggi isolati')
    names = set()
    if not cfg['modelli']:
        raise ValueError('Lista modelli vuota')
    for m in cfg['modelli']:
        if not re.fullmatch(r'[a-z0-9_]+', m['nome']) or m['nome'] in names:
            raise ValueError('Nome modello duplicato o non valido')
        names.add(m['nome'])
        if m['backend'] not in {'gliner', 'gliner2', 'transformers'}:
            raise ValueError('Backend non supportato')
        if not 0 <= m['soglia'] <= 1 or type(m['max_tokens']) is not int or m['max_tokens'] < 2:
            raise ValueError('Soglia o limite non valido')
        if not m['repository'] or not m['revision'] or not m['etichette']:
            raise ValueError('Repository, revisione ed etichette obbligatori')
        if any(t is not None and t not in TIPI for t in m['etichette'].values()):
            raise ValueError('Mappatura etichette non valida')
        if set(m['unisci_adiacenti']) - TIPI:
            raise ValueError('Categorie di aggregazione non valide')
    inputs = leggi(ROOT / cfg['input'])
    gold = leggi(ROOT / cfg['attese'])
    # Valida i riferimenti prima di scaricare pesi o creare cartelle.
    valuta(inputs, gold, [])
    return cfg, inputs, gold


def normalizza(raw, testo, m):
    mapped = []; ignorate = Counter()
    for a in raw:
        label = a.get('entity_group', a.get('label'))
        if label not in m['etichette']:
            raise ValueError(f'Etichetta inattesa: {label}')
        tipo = m['etichette'][label]
        start, end, score = int(a['start']), int(a['end']), float(a['score'])
        if not 0 <= start < end <= len(testo) or not math.isfinite(score):
            raise ValueError('Span o score del modello non valido')
        # Alcuni tokenizer includono negli offset gli spazi adiacenti all'entità.
        # Il formato comune usa invece i confini del solo contenuto identificativo.
        while start < end and testo[start].isspace():
            start += 1
        while end > start and testo[end-1].isspace():
            end -= 1
        if start == end:
            raise ValueError('Span vuoto dopo la normalizzazione degli spazi')
        if tipo is None:
            ignorate[label] += 1
            continue
        if score < m['soglia']:
            continue
        mapped.append(dict(start=start, end=end, tipo=tipo, score=score))
    # Score non confrontati tra modelli. Conflitti risolti solo nella stessa risposta.
    selected = []
    for a in sorted(mapped, key=lambda x: (-x['score'], -(x['end']-x['start']), x['start'], x['tipo'])):
        if not any(a['start'] < b['end'] and a['end'] > b['start'] for b in selected):
            selected.append(a)
    result = []
    for a in sorted(selected, key=lambda x: x['start']):
        if (result and a['tipo'] in m['unisci_adiacenti'] and result[-1]['tipo'] == a['tipo']
                and re.fullmatch(r'[\s,]*', testo[result[-1]['end']:a['start']])):
            result[-1]['end'] = a['end']
            result[-1]['score'] = min(result[-1]['score'], a['score'])
        else:
            result.append(dict(a))
    for a in result:
        a['testo'] = testo[a['start']:a['end']]
    return result, dict(ignorate)


def predici(record, m, infer):
    spans = []; raw_messages = []; ignorate = Counter()
    start = time.perf_counter()
    try:
        for i, message in enumerate(record['conversazione']):
            testo = message['testo']
            raw = infer(testo) if testo.strip() else []
            raw_messages.append({'campo': f'conversazione.{i}.testo', 'entita': raw})
            normalized, ignored = normalizza(raw, testo, m)
            ignorate.update(ignored)
            spans.extend({'campo': f'conversazione.{i}.testo', **a} for a in normalized)
        span_validi(spans, record['conversazione'])
        return {'id': record['id'], 'stato': 'ok', 'annotazioni': spans,
                'etichette_ignorate': dict(ignorate), 'secondi': time.perf_counter()-start}, raw_messages
    except Exception as error:
        return {'id': record['id'], 'stato': 'errore', 'errore': f'{type(error).__name__}: {error}',
                'secondi': time.perf_counter()-start}, raw_messages


def converti_gliner2(result):
    if not isinstance(result, dict) or not isinstance(result.get('entities'), dict):
        raise ValueError('Risultato GLiNER2 non valido')
    raw = []
    for label, entities in result['entities'].items():
        if not isinstance(entities, list):
            raise ValueError('Entità GLiNER2 non valide')
        for entity in entities:
            if not isinstance(entity, dict) or not {'start', 'end'} <= entity.keys():
                raise ValueError('Offset GLiNER2 mancanti')
            raw.append({'label': label, 'start': int(entity['start']), 'end': int(entity['end']),
                        'score': float(entity.get('confidence', 1.0))})
    return raw


def backend(m, device, metadata):
    # Import e accesso alla rete avvengono soltanto nell'esecuzione esplicita.
    from huggingface_hub import HfApi, snapshot_download
    sha = HfApi().model_info(m['repository'], revision=m['revision']).sha
    metadata['revision_risolta'] = sha
    folder = snapshot_download(m['repository'], revision=sha)
    import torch
    if device.startswith('cuda') and not torch.cuda.is_available():
        raise ValueError('CUDA non disponibile: nessun fallback silenzioso su CPU')
    if m['backend'] == 'transformers':
        from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
        tokenizer = AutoTokenizer.from_pretrained(folder, use_fast=True, trust_remote_code=False)
        if not tokenizer.is_fast:
            raise ValueError('Serve un tokenizer con offset')
        model = AutoModelForTokenClassification.from_pretrained(folder, trust_remote_code=False)
        actual = {re.sub(r'^[BI]-', '', v) for v in model.config.id2label.values()} - {'O'}
        if actual - m['etichette'].keys():
            raise ValueError(f'Etichette non configurate: {sorted(actual - m["etichette"].keys())}')
        pipe = pipeline('token-classification', model=model, tokenizer=tokenizer,
                        aggregation_strategy='simple', device=device)
        limite = min(m['max_tokens'], tokenizer.model_max_length)
        def infer(text):
            if len(tokenizer(text, truncation=False)['input_ids']) > limite:
                raise ValueError(f'Messaggio oltre il limite di {limite} token; non troncato')
            return [{k: (float(a[k]) if k == 'score' else int(a[k]) if k in {'start','end'} else a[k])
                     for k in ('entity_group','start','end','score')} for a in pipe(text)]
    elif m['backend'] == 'gliner':
        from gliner import GLiNER
        model = GLiNER.from_pretrained(folder).to(device)
        model.eval()
        processor = model.data_processor
        labels = list(m['etichette'])
        def infer(text):
            words = [item[0] for item in processor.words_splitter(text)]
            if len(words) > model.config.max_len:
                raise ValueError('Messaggio oltre il limite di parole GLiNER; non troncato')
            # Conta anche il prompt delle etichette, con la stessa tokenizzazione del modello.
            prepared, _ = processor.prepare_inputs([words], [labels])
            if processor.preprocess_text:
                prepared = processor.prepare_texts(prepared)
            tokenizer = processor.transformer_tokenizer
            tokens = tokenizer(prepared, is_split_into_words=True, truncation=False)['input_ids'][0]
            if len(tokens) > min(m['max_tokens'], tokenizer.model_max_length):
                raise ValueError('Messaggio e categorie oltre il limite token GLiNER; non troncati')
            with torch.inference_mode():
                entities = model.predict_entities(text, labels, threshold=m['soglia'], flat_ner=True)
            return [{k: (float(a[k]) if k=='score' else int(a[k]) if k in {'start','end'} else a[k])
                     for k in ('label','start','end','score')} for a in entities]
    else:
        from gliner2 import AutoExtractor
        model = AutoExtractor.from_pretrained(str(folder), map_location=device)
        if hasattr(model, 'eval'):
            model.eval()
        labels = list(m['etichette'])
        def infer(text):
            if len(text.split()) > m['max_tokens']:
                raise ValueError(f'Messaggio oltre il limite di {m["max_tokens"]} parole GLiNER2; non troncato')
            result = model.extract_entities(text, labels, threshold=m['soglia'],
                                            include_confidence=True, include_spans=True)
            return converti_gliner2(result)
    return infer


def esegui(cfg, inputs, gold, device, loader=backend):
    out = ROOT / cfg['output']
    out.mkdir(parents=True, exist_ok=False)
    salva(out/'config.json', cfg)
    versions = {}
    for package in ('torch','transformers','gliner','gliner2','huggingface-hub'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    salva(out/'manifest.json', {'contesto':cfg['contesto'], 'device':device, 'librerie':versions,
          'fonti':{key: {'path':str((ROOT/cfg[key]).resolve()),
                         'sha256':hashlib.sha256((ROOT/cfg[key]).read_bytes()).hexdigest()}
                   for key in ('input','attese')}})
    summary = []
    for m in cfg['modelli']:
        print(f"Modello: {m['nome']}", flush=True)
        directory = out / m['nome']; directory.mkdir()
        metadata = {'modello':m, 'categorie_mappate': sorted(set(m['etichette'].values())-{None})}
        infer = None
        model_start = time.perf_counter()
        try:
            load_start = time.perf_counter()
            infer = loader(m, device, metadata)
            import sys
            torch = sys.modules.get('torch')
            usa_cuda = bool(torch and device.startswith('cuda') and torch.cuda.is_available())
            if usa_cuda:
                torch.cuda.synchronize(device)
                torch.cuda.reset_peak_memory_stats(device)
            load_seconds = time.perf_counter() - load_start
            inference_start = time.perf_counter()
            predictions = []
            with (directory/'predizioni.jsonl').open('x', encoding='utf-8') as pf, (directory/'predizioni_native.jsonl').open('x', encoding='utf-8') as rf:
                for r in inputs:
                    prediction, raw = predici(r, m, infer)
                    predictions.append(prediction)
                    pf.write(json.dumps(prediction, ensure_ascii=False)+'\n'); pf.flush()
                    rf.write(json.dumps({'id':r['id'], 'messaggi':raw}, ensure_ascii=False)+'\n'); rf.flush()
            if usa_cuda:
                torch.cuda.synchronize(device)
            inference_seconds = time.perf_counter() - inference_start
            report = valuta(inputs, gold, predictions)
            salva(directory/'valutazione.json', report)
            performance = {
                'secondi_caricamento': load_seconds,
                'secondi_inferenza': inference_seconds,
                'secondi_totali': time.perf_counter() - model_start,
                'picco_vram_allocata_byte': int(torch.cuda.max_memory_allocated(device)) if usa_cuda else None,
                'picco_vram_riservata_byte': int(torch.cuda.max_memory_reserved(device)) if usa_cuda else None,
            }
            metadata['prestazioni'] = performance
            summary.append({'modello':m['nome'], 'stato':'completato' if not report['fallimenti_tecnici'] else 'parziale',
                            'valutate':report['conversazioni_valutate'], 'totali':len(inputs),
                            'fallimenti':len(report['fallimenti_tecnici']), 'metriche':report['span_esatti_micro'],
                            'prestazioni':performance})
        except Exception as error:
            metadata['errore'] = f'{type(error).__name__}: {error}'
            metadata['secondi_fino_errore'] = time.perf_counter() - model_start
            summary.append({'modello':m['nome'], 'stato':'errore', 'errore':metadata['errore']})
        finally:
            salva(directory/'manifest.json', metadata)
            infer = None
            gc.collect()
            import sys
            if 'torch' in sys.modules and sys.modules['torch'].cuda.is_available():
                sys.modules['torch'].cuda.empty_cache()
        print(summary[-1], flush=True)
    salva(out/'riepilogo.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'config/esperimento_modelli.json')
    parser.add_argument('--solo-controllo', action='store_true')
    parser.add_argument('--device', default='cpu', help='cpu oppure cuda:0 sulla macchina GPU')
    args = parser.parse_args()
    try:
        cfg, inputs, gold = carica(args.config)
        if (ROOT/cfg['output']).exists():
            raise ValueError('Cartella output già esistente; scegliere un nuovo esperimento')
        if args.solo_controllo:
            print(f'Conversazioni: {len(inputs)}; modelli: {len(cfg["modelli"])}; contesto: {cfg["contesto"]}')
            for m in cfg['modelli']:
                print(f"{m['nome']}: {m['repository']} — categorie mappate: {sorted(set(m['etichette'].values())-{None})}")
            print('Nessun download o inferenza. Licenze e limiti: docs/confronto_modelli.md')
            return
        summary = esegui(cfg, inputs, gold, args.device)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    if any(r['stato'] != 'completato' for r in summary):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
