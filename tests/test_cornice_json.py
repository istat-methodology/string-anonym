import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from validazione import prepara_testo
from rivalida_chat import rivalida


class CorniceTest(unittest.TestCase):
    def setUp(self):
        self.scheda = {'modalita':'senza_dati_personali', 'metadati_fissati':{'data_sintetica':'2026-09-27','chiave_indagine':None}, 'entita_previste':[], 'numero_scambi':1}
        self.chat = {'metadati':{**self.scheda['metadati_fissati'],'descrizione':'Ricerca dati'}, 'conversazione':[{'sender':'Utente','testo':'Cerco dati.'},{'sender':'Agente','testo':'Per quale periodo?'}], 'trattamento_atteso':{'mascherare':[],'conservare':[],'motivazione':'Nessuna entità.'}}
        self.testo = json.dumps(self.chat)

    def test_json_puro_e_cornice_equivalenti(self):
        puro = prepara_testo(self.testo, self.scheda)
        self.assertEqual(puro['validazione']['correzioni'], [])
        for apertura in ['```json', '```']:
            for newline in ['\n','\r\n']:
                testo = ' \n' + apertura + newline + self.testo + newline + '```\n '
                risultato = prepara_testo(testo, self.scheda)
                self.assertEqual(risultato['chat'], puro['chat'])
                self.assertEqual(len(risultato['validazione']['correzioni']), 1)

    def test_rifiuta_testo_esterno_blocchi_multipli_e_json_errato(self):
        blocco = '```json\n' + self.testo + '\n```'
        for testo in ['Ecco il risultato:\n'+blocco, blocco+'\nFine.', blocco+'\n'+blocco,
                      '```python\n'+self.testo+'\n```', '```json\n{"a":}\n```',
                      '```json\n'+self.testo, '```json\n[]\n```']:
            with self.subTest(testo=testo[:40]), self.assertRaises(ValueError):
                prepara_testo(testo, self.scheda)

    def test_rivalidazione_conserva_originale_e_controlli(self):
        testo = '```json\n'+self.testo+'\n```'
        record = {'provider':'anthropic','stato':'da_verificare','errore':'Vecchio errore JSON',
                  'prompt':{'scheda':self.scheda}, 'risposta_originale':{'stop_reason':'end_turn','content':[{'type':'text','text':testo}]}}
        originale = copy.deepcopy(record)
        risultato = rivalida(record)
        self.assertEqual(risultato['stato'], 'valido')
        self.assertEqual(risultato['verifica_precedente']['errore'], 'Vecchio errore JSON')
        self.assertEqual(risultato['risposta_originale'], originale['risposta_originale'])
        self.assertEqual(record, originale)
        self.assertEqual(len(risultato['validazione']['correzioni']), 1)
        record['risposta_originale']['stop_reason'] = 'max_tokens'
        self.assertEqual(rivalida(record)['stato'], 'da_verificare')


if __name__ == '__main__': unittest.main()
