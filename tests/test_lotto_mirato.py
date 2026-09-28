import copy
from collections import Counter
from datetime import date
from pathlib import Path
import sys
import tempfile
import json
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from genera_prompt import carica_scenari, genera
from parse_input import DatiInput, leggi_indagini
from validazione import prepara_chat
ROOT=Path(__file__).resolve().parents[1]


class MiratoTest(unittest.TestCase):
    def setUp(self):
        self.catalogo=carica_scenari(ROOT/'config/scenari_mirati_v4_2.json')
        self.dati=DatiInput(['Anna'],['Rossi'],{'001001':'Alfa'},[('001001','VIA ROMA')],{})
        self.dati.indagini=leggi_indagini(ROOT/'data/codici_psn.csv')
        self.rows=list(genera(self.catalogo,1,0,date(2026,4,1),21,self.dati))

    def test_totale_bilanciato(self):
        def lotto(totale):
            return list(genera(self.catalogo, 2, 100, date(2026,4,1), 21, self.dati, totale=totale))
        rows = lotto(100)
        self.assertEqual(rows, lotto(100))
        self.assertEqual(len(rows), 100)
        self.assertEqual(len({r['id'] for r in rows}), 100)
        self.assertEqual(Counter(r['scheda']['modalita'] for r in rows),
                         {'con_dati_personali': 50, 'senza_dati_personali': 50})
        counts = Counter((r['scheda']['scenario'], r['scheda']['modalita']) for r in rows)
        self.assertEqual(Counter(counts.values()), {4: 20, 5: 4})
        for scenario in self.catalogo['scenari']:
            self.assertEqual(counts[scenario['id'], 'con_dati_personali'],
                             counts[scenario['id'], 'senza_dati_personali'])
        for totale in (0, -2, 99):
            with self.assertRaises(ValueError):
                lotto(totale)

    def test_copertura_prevista_e_riproducibilita(self):
        self.assertEqual(self.rows,list(genera(self.catalogo,1,0,date(2026,4,1),21,self.dati)))
        self.assertEqual(len(self.rows),24)
        self.assertEqual(len({r['id'] for r in self.rows}),24)
        counts=Counter()
        for r in self.rows:
            s=r['scheda']; es=s['entita_previste']; target=s['copertura_mirata']
            if s['modalita']=='senza_dati_personali':
                self.assertEqual(es,[]);self.assertEqual(target['ripetere_agente'],[])
            else:
                counts.update(e['tipo'] for e in es)
                self.assertTrue(target['ripetere_agente'])
                self.assertTrue(set(target['ripetere_agente']) <= {e['segnaposto'] for e in es})
                if s['scenario'].startswith('mirato_referente'):
                    email=next(e['valore_proposto'] for e in es if e['tipo']=='EMAIL')
                    self.assertNotIn('rossi',email)
        for label in ('PASSWORD','COD_UTENTE','NUM_PRATICA','PHONE'):
            self.assertEqual(counts[label],4)

    def test_controlli_effettivi_e_span(self):
        for r in self.rows:
            s=r['scheda']; es=s['entita_previste']; target=s['copertura_mirata']
            slots=' '.join(e['segnaposto'] for e in es)
            riferimenti=' '.join(target['riferimenti_letterali'])
            chat={'metadati':{**s['metadati_fissati'],'descrizione':'Richiesta di chiarimenti.'},'conversazione':[{'sender':'Utente','testo':'Chiedo: '+slots+' '+riferimenti},{'sender':'Agente','testo':'Si riferisce a '+slots+'?'}], 'trattamento_atteso':{'mascherare':[{k:e[k] for k in ('segnaposto','tipo','sostituzione')} for e in es],'conservare':[],'motivazione':'Prova locale.'}}
            result=prepara_chat(chat,s)
            self.assertEqual(result['stato'],'valido')
            if es:
                chat['conversazione'][1]['testo']='Quale problema ha riscontrato?'
                result=prepara_chat(chat,s)
                self.assertEqual(result['stato'],'da_verificare')
                self.assertTrue(result['validazione']['segnali_copertura'])
                self.assertTrue(result['chat']['trattamento_atteso']['mascherare'])
            if riferimenti:
                chat['conversazione'][0]['testo']='Chiedo: '+slots
                self.assertTrue(prepara_chat(chat,s)['validazione']['segnali_copertura'])

    def test_configurazione_ripetizione_sconosciuta(self):
        c=copy.deepcopy(self.catalogo);c['scenari'][0]['ripetere_agente']=['inesistente']
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'catalogo.json';p.write_text(json.dumps(c))
            with self.assertRaises(ValueError):carica_scenari(p)


if __name__=='__main__':unittest.main()
