import copy
from pathlib import Path
import sys
import unittest
import tempfile
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from esegui_generazione import seleziona, riepilogo_esistente, prossimo_segmento, verifica_piano_ripresa
from genera_chat import parametri_richiesta


class EsecuzioneGenerazioneTest(unittest.TestCase):
    def test_riepilogo_esistente_completo_parziale_e_incompatibile(self):
        with tempfile.TemporaryDirectory() as directory:
            cartella = Path(directory)
            self.assertIn('senza risultato finale', riepilogo_esistente(cartella, [self.prompt], 'modello'))
            finale = cartella / 'conversazioni.jsonl'
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
            self.assertIn('Generazione incompleta', riepilogo_esistente(cartella, [self.prompt], 'modello'))
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
        mancanti, riusati, _ = seleziona(
            [self.prompt], [('test.jsonl', {**self.record, 'stato':'errore_api', 'risposta_originale':None})],
            'modello', 'https://risorsa/openai/v1/', 6000, ignora_errori_api=True)
        self.assertEqual(mancanti, [self.prompt]); self.assertFalse(riusati)
        with self.assertRaises(ValueError): self.scegli([], [self.prompt,self.prompt])
        secondo = copy.deepcopy(self.record); secondo['risposta_originale']['id']='altra'
        with self.assertRaises(ValueError): self.scegli([self.record,secondo])
        self.assertEqual(len(self.scegli([self.record,self.record])[1]),1)

    def test_verifica_piano_e_numera_segmenti_di_ripresa(self):
        with tempfile.TemporaryDirectory() as directory:
            cartella = Path(directory)
            input_path = cartella / 'prompts.jsonl'
            piano = {'input': str(input_path), 'deployment': 'modello',
                     'endpoint': 'https://risorsa/openai/v1/', 'max_output_tokens': 6000,
                     'id_previsti': ['caso-1']}
            (cartella / 'piano.json').write_text(json.dumps(piano))
            verifica_piano_ripresa(cartella, [self.prompt], input_path, 'modello',
                                   'https://risorsa/openai/v1', 6000)
            pending, output = prossimo_segmento(cartella)
            self.assertTrue(pending.name.endswith('001.jsonl'))
            output.touch()
            self.assertTrue(prossimo_segmento(cartella)[1].name.endswith('002.jsonl'))
            with self.assertRaises(ValueError):
                verifica_piano_ripresa(cartella, [self.prompt], input_path, 'altro',
                                       'https://risorsa/openai/v1', 6000)


if __name__ == '__main__': unittest.main()
