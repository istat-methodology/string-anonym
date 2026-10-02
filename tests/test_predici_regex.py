import copy
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from predici_regex import carica_regole, detect_regex, riconosci, predici, ROOT
from valuta_masking import span_validi


class RegexTest(unittest.TestCase):
    def setUp(self):
        self.config=carica_regole(ROOT/'config/regole_masking.json')

    def test_formati_e_confini(self):
        cases=[('Scriva a a.b@example.org.', 'a.b@example.org','EMAIL'),
               ('Prot.n. 1589563/25','1589563/25','NUM_PRATICA'),
               ('telefono +39 333.123.4567','+39 333.123.4567','PHONE'),
               ('Uso P012345678','P012345678','COD_UTENTE'),
               ('codice utente 012345678','012345678','COD_UTENTE'),
               ('password Abc123!','Abc123!','PASSWORD'),
               ('password: abcDEF!','abcDEF!','PASSWORD')]
        for testo,valore,tipo in cases:
            with self.subTest(testo=testo):
                a=riconosci(testo,self.config['regole'])
                self.assertEqual([(s['testo'],s['tipo']) for s in a],[(valore,tipo)])
                self.assertEqual(testo[a[0]['start']:a[0]['end']],valore)

    def test_negativi(self):
        for testo in ['IST-00070, anno 2024, 123456 abitanti.', 'La password non funziona.',
                      'Ho dimenticato la password', 'Cerco dati su Roma.', '123333123456789']:
            self.assertEqual(riconosci(testo,self.config['regole']),[],testo)

    def test_conflitti_ruoli_e_input_invariato(self):
        r={'id':'test','conversazione':[{'sender':'Utente','testo':'codice utente 3331234567'},
                                       {'sender':'Agente','testo':'pratica 3331234567'}]}
        before=copy.deepcopy(r)
        p=predici(r,self.config)
        self.assertEqual([a['tipo'] for a in p['annotazioni']],['COD_UTENTE','NUM_PRATICA'])
        self.assertEqual([d['type'] for d in p['detections']],
                         ['COD_UTENTE','PHONE','NUM_PRATICA','PHONE'])
        span_validi(p['annotazioni'],r['conversazione'])
        self.assertEqual(r,before)
        self.assertEqual(predici({'id':'bad','conversazione':None},self.config)['stato'],'errore')

    def test_detection_regex_non_risolve_sovrapposizioni(self):
        rules = [
            {'nome':'lunga', 'tipo':'PASSWORD', 'priorita':2,
             'regex':re.compile(r'(?P<valore>abc123)')},
            {'nome':'corta', 'tipo':'COD_UTENTE', 'priorita':1,
             'regex':re.compile(r'(?P<valore>abc)')},
        ]
        detections=detect_regex('abc123', rules, 'conversazione.0.testo')
        self.assertEqual(len(detections),2)


if __name__=='__main__':unittest.main()
