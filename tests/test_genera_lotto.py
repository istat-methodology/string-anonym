import copy
from pathlib import Path
import sys
import unittest
import tempfile
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genera_lotto import seleziona, riepilogo_esistente
from genera_chat import parametri_richiesta


class LottoTest(unittest.TestCase):
    def test_riepilogo_esistente_completo_parziale_e_incompatibile(self):
        with tempfile.TemporaryDirectory() as directory:
            cartella = Path(directory)
            self.assertIn('senza risultato finale', riepilogo_esistente(cartella, [self.prompt], 'modello'))
            finale = cartella / 'chat_lotto.jsonl'
            finale.write_text(json.dumps(self.record) + '\n')
            testo = riepilogo_esistente(cartella, [self.prompt], 'modello')
            self.assertIn('Risposte presenti: 1/1; valide: 1', testo)
            self.assertNotIn('nuove chiamate', testo)
            with self.assertRaises(ValueError):
                riepilogo_esistente(cartella, [self.prompt], 'altro-modello')
            with self.assertRaises(ValueError):
                riepilogo_esistente(cartella, [{**self.prompt, 'messages': []}], 'modello')
            finale.write_text(json.dumps(self.record) + '\n' + json.dumps(self.record))
            with self.assertRaises(ValueError):
                riepilogo_esistente(cartella, [self.prompt], 'modello')
            finale.write_text('')
            self.assertIn('Lotto incompleto', riepilogo_esistente(cartella, [self.prompt], 'modello'))
            finale.write_text(json.dumps({**self.record, 'stato': 'errore_api'}))
            self.assertIn('errori API: 1', riepilogo_esistente(cartella, [self.prompt], 'modello'))

    def setUp(self):
        self.prompt = {'id':'caso-1', 'messages':[{'role':'user','content':'Scheda'}]}
        self.record = {'id':'caso-1', 'prompt':self.prompt, 'provider':'openai', 'deployment':'modello',
                       'endpoint':'https://risorsa/openai/v1/', 'stato':'valido',
                       'risposta_originale':{'status':'completed'},
                       'parametri_api':parametri_richiesta(self.prompt,'modello',6000,'openai')}

    def scegli(self, records, prompts=None):
        return seleziona(prompts or [self.prompt], [('test.jsonl', r) for r in records], 'modello', 'https://risorsa/openai/v1/', 6000)

    def test_riusa_anche_da_verificare(self):
        for stato in ['valido','da_verificare']:
            r = {**self.record,'stato':stato}
            mancanti, riusati, fonti = self.scegli([r])
            self.assertEqual(mancanti,[])
            self.assertEqual(riusati['caso-1'],r)
            self.assertEqual(fonti['caso-1'],'test.jsonl')

    def test_stesso_id_non_basta(self):
        for campo, valore in [('prompt',{'id':'caso-1','messages':[]}),('provider','anthropic'),
                              ('deployment','altro'),('endpoint','https://altra/'),('parametri_api',{})]:
            with self.subTest(campo=campo):
                mancanti, riusati, _ = self.scegli([{**self.record,campo:valore}])
                self.assertEqual(mancanti,[self.prompt]); self.assertFalse(riusati)

    def test_rifiuta_errori_api_duplicati_e_ambiguita(self):
        with self.assertRaises(ValueError): self.scegli([{**self.record,'stato':'errore_api'}])
        with self.assertRaises(ValueError): self.scegli([], [self.prompt,self.prompt])
        secondo = copy.deepcopy(self.record); secondo['risposta_originale']['id']='altra'
        with self.assertRaises(ValueError): self.scegli([self.record,secondo])
        self.assertEqual(len(self.scegli([self.record,self.record])[1]),1)


if __name__ == '__main__': unittest.main()
