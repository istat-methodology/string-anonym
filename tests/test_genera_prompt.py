import random
import sys
import unittest
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genera_prompt import carica_scenari, genera
from parse_input import DatiInput, leggi_indagini

class PromptTest(unittest.TestCase):
    def test_scenari_modalita_e_contesto(self):
        catalogo = carica_scenari(Path(__file__).resolve().parents[1] / 'config/scenari.json')
        dati = DatiInput(['Anna'], ['Rossi'], {'001001': 'Alfa'}, [('001001', 'VIA ROMA')], {})
        dati.indagini = leggi_indagini(Path(__file__).resolve().parents[1] / 'data/codici_psn.csv')
        args = (catalogo, 2, 42, date(2026, 4, 1), 21, dati)
        righe = list(genera(*args))
        self.assertEqual(righe, list(genera(*args)))
        self.assertEqual(len(righe), 46)
        self.assertEqual(len({r['id'] for r in righe}), 46)
        for r in righe:
            s = r['scheda']
            self.assertEqual(r['versione_prompt'], '5.0-draft4')
            self.assertEqual(s['schema_output'], 'chat_v5')
            self.assertIn('riferimenti_detection', s)
            self.assertIn('ipotesi_policy', r)
            self.assertNotIn('canale', s['metadati_fissati'])
            self.assertIsNone(s['metadati_fissati']['chiave_indagine'])
            if s['indagine']:
                self.assertEqual(s['indagine']['tipo_rispondente'], s['tipo_rispondente'])
            self.assertEqual(bool(s['entita_previste']), s['modalita'] == 'con_dati_personali')
            if s['scenario'] == 'ricerca_dati_territoriali':
                self.assertEqual(s['contesto_statistico']['comune'], 'Alfa')
                self.assertIsNone(s['metadati_fissati']['chiave_indagine'])
                self.assertIsNone(s['nome_indagine'])
                self.assertNotIn('ADDRESS', [e['tipo'] for e in s['entita_previste']])
                tipi = {e['tipo'] for e in s['riferimenti_detection']}
                self.assertTrue({'LOCATION', 'DATE'} <= tipi)

    def test_email_del_nuovo_contatto_indipendente(self):
        dati = DatiInput(['Anna'], ['Rossi'], {'001001': 'Alfa'}, [('001001', 'VIA ROMA')], {})
        normale = dati.campiona(random.Random(42), ['persona_1', 'email_1'])
        separata = dati.campiona(random.Random(42), ['persona_1', 'email_1'], email_indipendente=True)
        self.assertEqual(normale['email_1'], 'anna.rossi@example.org')
        self.assertTrue(separata['email_1'].startswith('contatto.'))
        self.assertNotIn('rossi', separata['email_1'])
        self.assertEqual(separata, dati.campiona(random.Random(42), ['persona_1', 'email_1'], email_indipendente=True))

if __name__ == '__main__': unittest.main()
