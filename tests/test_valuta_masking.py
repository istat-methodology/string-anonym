"""Prova controllata del valutatore: non misura un modello di masking."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from valuta_masking import valuta


def span(start, end, tipo='PERSON'):
    return {'campo':'conversazione.0.testo', 'start':start, 'end':end, 'tipo':tipo}


class ValutatoreTest(unittest.TestCase):
    def setUp(self):
        self.inputs = [{'id':'a','conversazione':[{'sender':'Utente','testo':'È Anna.'}]},
                       {'id':'b','conversazione':[{'sender':'Agente','testo':'Roma'}]}]
        self.gold = [{'id':'a','annotazioni':[span(2,6)]}, {'id':'b','annotazioni':[]}]
        self.pred = [{'id':'a','stato':'ok','annotazioni':[span(2,6)]},
                     {'id':'b','stato':'ok','annotazioni':[]}]

    def test_perfetto_e_negativo(self):
        r = valuta(self.inputs,self.gold,self.pred)
        self.assertEqual(r['span_esatti_micro'],dict(tp=1,fp=0,fn=0,precision=1,recall=1,f1=1))
        self.assertEqual(r['negative_valutate'],1)
        self.assertIsNone(r['per_tipo']['PHONE']['recall'])

    def test_confini_parziali_e_falso_positivo(self):
        self.pred[0]['annotazioni']=[span(2,5)]
        self.pred[1]['annotazioni']=[span(0,4,'ADDRESS')]
        r=valuta(self.inputs,self.gold,self.pred)
        self.assertEqual([r['span_esatti_micro'][k] for k in ('tp','fp','fn')],[0,2,1])
        self.assertEqual(r['caratteri']['recall_copertura'],0.75)
        self.assertEqual(r['caratteri']['non_sensibili_mascherati'],4)
        self.assertEqual(r['negative_con_falsi_positivi'],1)
        self.assertEqual(r['per_ruolo']['Agente']['fp'],1)

    def test_tipo_errato_ma_caratteri_coperti(self):
        self.pred[0]['annotazioni']=[span(2,6,'ADDRESS')]
        r=valuta(self.inputs,self.gold,self.pred)
        self.assertEqual(r['span_esatti_micro']['fn'],1)
        self.assertEqual(r['caratteri']['recall_copertura'],1)
        self.assertEqual(r['conversazioni_con_omissioni_caratteri'],0)

    def test_fallimenti_non_diventano_negativi(self):
        r=valuta(self.inputs,self.gold,[{'id':'a','stato':'errore','errore':'Memoria esaurita'}])
        self.assertEqual(r['conversazioni_valutate'],0)
        self.assertEqual(len(r['fallimenti_tecnici']),2)
        self.assertIsNone(r['span_esatti_micro']['f1'])

    def test_predizione_vuota_e_omissione(self):
        self.pred[0]['annotazioni']=[]
        r=valuta(self.inputs,self.gold,self.pred)
        self.assertEqual(r['span_esatti_micro']['fn'],1)
        self.assertEqual(r['conversazioni_con_omissioni_caratteri'],1)
        self.assertEqual(r['caratteri']['recall_copertura'],0)

    def test_formati_invalidi(self):
        for annotazioni in ([span(2,6),span(2,6)], [span(2,99)], [span(2,6,'ALTRO')],
                            [{**span(2,6),'testo':'sbagliato'}]):
            with self.subTest(annotazioni=annotazioni):
                pred=copy.deepcopy(self.pred);pred[0]['annotazioni']=annotazioni
                with self.assertRaises(ValueError):valuta(self.inputs,self.gold,pred)
        with self.assertRaises(ValueError):valuta(self.inputs,self.gold,self.pred+self.pred)
        with self.assertRaises(ValueError):valuta(self.inputs,self.gold,[{'id':'estraneo'}])
        with self.assertRaises(ValueError):valuta(self.inputs,self.gold[:1],self.pred)


if __name__ == '__main__':
    unittest.main(verbosity=2)
