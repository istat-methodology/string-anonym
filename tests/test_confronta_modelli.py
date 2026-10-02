import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from confronta_modelli import ROOT, carica, converti_gliner2, detect_model, esegui, normalizza, predici


class ConfrontoTest(unittest.TestCase):
    def setUp(self):
        self.model = dict(nome='fake', backend='transformers', repository='test/model', revision='main',
                          max_tokens=256, soglia=0.0, etichette={'GIVENNAME':'PERSON','SURNAME':'PERSON','CITY':None},
                          unisci_adiacenti=['PERSON'])
        self.record = {'id':'a', 'conversazione':[{'sender':'Utente','testo':'È Anna Rossi, Roma.'}]}
        self.raw = [{'entity_group':'GIVENNAME','start':2,'end':6,'score':0.9},
                    {'entity_group':'SURNAME','start':7,'end':12,'score':0.8},
                    {'entity_group':'CITY','start':14,'end':18,'score':0.99}]

    def test_mapping_unicode_e_aggregazione(self):
        spans, ignored = normalizza(self.raw, self.record['conversazione'][0]['testo'], self.model)
        self.assertEqual(spans[0]['testo'],'Anna Rossi')
        self.assertEqual((spans[0]['start'],spans[0]['end']),(2,12))
        self.assertEqual(ignored,{'CITY':1})
        self.assertEqual(len(spans),1)

    def test_rimuove_spazi_esterni_dagli_offset(self):
        raw = [dict(label='GIVENNAME', start=0, end=6, score=0.9)]
        spans, ignored = normalizza(raw, ' Anna ', self.model)
        self.assertEqual(ignored, {})
        self.assertEqual(spans, [dict(start=1, end=5, tipo='PERSON', score=0.9, testo='Anna')])

    def test_rifiuta_span_di_soli_spazi(self):
        raw = [dict(label='GIVENNAME', start=0, end=2, score=0.9)]
        with self.assertRaisesRegex(ValueError, 'Span vuoto'):
            normalizza(raw, '  ', self.model)

    def test_conversione_output_gliner2(self):
        result = {'entities': {'person': [
            {'text':'Anna', 'start':2, 'end':6, 'confidence':0.91}
        ], 'address': []}}
        self.assertEqual(converti_gliner2(result), [
            {'label':'person', 'start':2, 'end':6, 'score':0.91}
        ])
        with self.assertRaisesRegex(ValueError, 'Offset'):
            converti_gliner2({'entities': {'person':[{'text':'Anna'}]}})

    def test_nessuna_fusione_attraverso_parole(self):
        raw=[dict(label='GIVENNAME',start=0,end=4,score=0.9),dict(label='SURNAME',start=7,end=12,score=0.9)]
        spans,_=normalizza(raw,'Anna e Rossi',self.model)
        self.assertEqual(len(spans),2)

    def test_sovrapposizioni_soglia_e_etichetta_ignota(self):
        m={**self.model, 'soglia':0.5}
        raw=[dict(label='GIVENNAME',start=2,end=12,score=0.99),*self.raw]
        spans,_=normalizza(raw,self.record['conversazione'][0]['testo'],m)
        self.assertEqual(len(spans),1)
        with self.assertRaises(ValueError):
            normalizza([dict(label='UNKNOWN',start=0,end=1,score=1)],'x',m)

    def test_detection_ner_conserva_sovrapposizioni(self):
        m={**self.model, 'soglia':0.5}
        raw=[dict(entity_group='GIVENNAME',start=2,end=12,score=0.99), *self.raw]
        detections, ignored=detect_model(raw, self.record['conversazione'][0]['testo'], m,
                                         'conversazione.0.testo')
        self.assertEqual(len(detections), 3)
        self.assertEqual(ignored, {'CITY':1})
        self.assertEqual({d['sources'][0]['native_type'] for d in detections},
                         {'GIVENNAME', 'SURNAME'})

    def test_errori_non_lasciano_predizioni_parziali(self):
        record=copy.deepcopy(self.record)
        record['conversazione'].append({'sender':'Agente','testo':'altro'})
        def infer(t):
            if t=='altro':raise ValueError('Limite token')
            return self.raw
        p,raw=predici(record,self.model,infer)
        self.assertEqual(p['stato'],'errore')
        self.assertNotIn('annotazioni',p)
        self.assertEqual(len(raw),1)

    def test_runner_sequenziale_e_valutazione_senza_gold_al_modello(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            inp=root/'input.jsonl'; gold=root/'gold.jsonl'
            inp.write_text(json.dumps(self.record))
            expected={'id':'a','annotazioni':[dict(campo='conversazione.0.testo',start=2,end=12,tipo='PERSON')]}
            gold.write_text(json.dumps(expected))
            cfg=dict(versione='1', contesto='messaggio_isolato', input=str(inp), attese=str(gold),
                     output=str(root/'run'), modelli=[{**self.model,'nome':'broken'},self.model])
            path=root/'config.json';path.write_text(json.dumps(cfg))
            cfg,inputs,attese=carica(path)
            seen=[]
            def loader(m,device,metadata):
                if m['nome']=='broken':raise RuntimeError('Caricamento fallito')
                metadata['revision_risolta']='fake-sha'
                def infer(t):
                    seen.append(t)
                    return self.raw
                return infer
            results=esegui(cfg,inputs,attese,'cpu',loader)
            self.assertEqual([r['stato'] for r in results],['errore','completato'])
            self.assertEqual(results[1]['metriche']['f1'],1)
            self.assertIsNone(results[1]['prestazioni']['picco_vram_allocata_byte'])
            self.assertIsNone(results[1]['prestazioni']['picco_vram_riservata_byte'])
            self.assertGreaterEqual(results[1]['prestazioni']['secondi_inferenza'], 0)
            self.assertEqual(seen,['È Anna Rossi, Roma.'])
            prediction=json.loads((root/'run/fake/predizioni.jsonl').read_text())
            self.assertIn('detections', prediction)
            self.assertTrue((root/'run/fake/predizioni_native.jsonl').exists())
            with self.assertRaises(FileExistsError):esegui(cfg,inputs,attese,'cpu',loader)

    def test_config_reale_senza_import_modelli(self):
        cfg=json.loads((ROOT/'config/esperimento_modelli.json').read_text())
        self.assertEqual(len(cfg['modelli']),4)
        wiki=next(m for m in cfg['modelli'] if m['nome']=='wikineural')
        self.assertIsNone(wiki['etichette']['LOC'])

    def test_config_puo_limitare_le_categorie_valutate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            inp=root/'input.jsonl'; gold=root/'gold.jsonl'
            inp.write_text(json.dumps(self.record))
            expected={'id':'a','annotazioni':[
                dict(campo='conversazione.0.testo',start=2,end=12,tipo='PERSON'),
                dict(campo='conversazione.0.testo',start=14,end=18,tipo='ADDRESS'),
            ]}
            gold.write_text(json.dumps(expected))
            cfg=dict(versione='1', contesto='messaggio_isolato', input=str(inp), attese=str(gold),
                     output=str(root/'run'), tipi_valutati=['PERSON'], modelli=[self.model])
            path=root/'config.json'; path.write_text(json.dumps(cfg))
            _, _, filtered=carica(path)
            self.assertEqual([a['tipo'] for a in filtered[0]['annotazioni']], ['PERSON'])


if __name__=='__main__':unittest.main()
