import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from esporta_dataset_masking import converti, esporta, leggi


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.r = {'id': 'caso', 'stato': 'valido', 'prompt': {'segreto': 'gold'}, 'chat': {
            'conversazione': [{'sender': 'Utente', 'testo': 'È Anna!'}, {'sender': 'Agente', 'testo': 'Anna, sì.'}],
            'metadati': {'descrizione': 'Anna'},
            'trattamento_atteso': {'mascherare': [
                {'campo': 'conversazione.0.testo', 'start': 2, 'end': 6, 'tipo': 'PERSON',
                 'testo': 'Anna', 'id_entita': 'p1', 'id_forma': 'completa', 'sostituzione': '[PERSON_1]'}]}}}

    def test_separazione_unicode_e_errori_span(self):
        original = copy.deepcopy(self.r)
        inp, gold, omitted = converti(self.r, 'id')
        self.assertEqual(set(inp), {'id', 'conversazione'})
        self.assertEqual(inp['conversazione'], self.r['chat']['conversazione'])
        self.assertEqual(len(gold['annotazioni']), 1)
        self.assertEqual(self.r, original)
        self.r['chat']['trattamento_atteso']['mascherare'][0]['end'] = 5
        with self.assertRaises(ValueError):
            converti(self.r, 'id')

    def test_export_esclusioni_revisioni_collisioni_e_no_sovrascrittura(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a, b = root/'a.jsonl', root/'b.jsonl'
            a.write_text(json.dumps(self.r)+'\n'+json.dumps({**self.r, 'id':'errore', 'stato':'da_verificare'}))
            b.write_text(json.dumps({**self.r, 'extra':'altra generazione'}))
            rev = root/'rev.json'
            rev.write_text(json.dumps({'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),
                                      'segnalazioni':[{'id':'caso', 'osservazione':'Controllare'}]}))
            result = esporta([a,b], root/'out', [rev])
            self.assertEqual((result['esportati'], result['esclusi']), (2,1))
            self.assertEqual(result['revisione_qualitativa'], {'segnalato':1, 'non_revisionato':1})
            self.assertEqual(len({r['id'] for r in leggi(root/'out/input.jsonl')}),2)
            with self.assertRaises(ValueError):esporta([a], root/'out')
            with self.assertRaises(ValueError):esporta([a,a], root/'duplicati')
            with self.assertRaises(ValueError):esporta([b], root/'errata', [rev])
            self.assertFalse((root/'errata').exists())

    def test_negativi_e_annotazioni_fuori_dialogo(self):
        self.r['chat']['trattamento_atteso']['mascherare'] = []
        self.assertEqual(converti(self.r,'id')[1]['annotazioni'], [])
        self.r['chat']['trattamento_atteso']['mascherare'] = [{'campo':'metadati.descrizione'}]
        self.assertEqual(converti(self.r,'id')[2], 1)
