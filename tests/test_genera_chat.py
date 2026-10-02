import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genera_chat import valida, sostituisci, prepara_chat

class ValidazioneTest(unittest.TestCase):
    def setUp(self):
        self.entita = {'segnaposto': '{{persona_1}}', 'tipo': 'PERSONA', 'sostituzione': '[PERSONA_1]', 'valore_proposto': 'Anna Rossi'}
        self.scheda = {'metadati_fissati': {'canale': 'Contact Centre', 'data_sintetica': '2026-04-01', 'chiave_indagine': '00070'}, 'numero_scambi': 1, 'entita_previste': [self.entita]}
        self.chat = {'metadati': {**self.scheda['metadati_fissati'], 'descrizione': 'Accesso'}, 'conversazione': [{'sender': 'Utente', 'testo': 'Sono {{persona_1}}'}, {'sender': 'Agente', 'testo': 'Come posso aiutarti?'}], 'trattamento_atteso': {'mascherare': [{k: self.entita[k] for k in ('segnaposto','tipo','sostituzione')}], 'conservare': [], 'motivazione': 'Mascherare il nome'}}

    def test_valido_e_sostituzione(self):
        valida(self.chat, self.scheda)
        risultato = sostituisci(self.chat['conversazione'], {'{{persona_1}}': 'Anna Rossi'})
        self.assertEqual(risultato[0]['testo'], 'Sono Anna Rossi')
        self.assertEqual(self.chat['conversazione'][0]['testo'], 'Sono {{persona_1}}')

    def test_rifiuta_metadati_ruoli_e_entita_errati(self):
        for modifica in ('chiave', 'ruolo', 'segnaposto', 'valore'):
            chat = copy.deepcopy(self.chat)
            if modifica == 'chiave': chat['metadati']['chiave_indagine'] = '70'
            if modifica == 'ruolo': chat['conversazione'][0]['sender'] = 'Agente'
            if modifica == 'segnaposto': chat['conversazione'][0]['testo'] = '{{persona_2}}'
            if modifica == 'valore': chat['conversazione'][0]['testo'] += ' Anna Rossi'
            with self.subTest(modifica=modifica), self.assertRaises(ValueError):
                valida(chat, self.scheda)

    def test_senza_entita(self):
        self.scheda['entita_previste'] = []
        self.chat['conversazione'][0]['testo'] = 'Come accedo?'
        self.chat['trattamento_atteso']['mascherare'] = []
        valida(self.chat, self.scheda)

    def test_alias_e_lunghezza_sono_documentati(self):
        self.chat['conversazione'][0]['text'] = self.chat['conversazione'][0].pop('testo')
        self.scheda['numero_scambi'] = 4
        risultato = prepara_chat(self.chat, self.scheda)
        self.assertEqual(risultato['stato'], 'valido')
        self.assertEqual(len(risultato['validazione']['correzioni']), 1)
        self.assertEqual(len(risultato['validazione']['avvisi']), 1)
        self.assertIn('text', self.chat['conversazione'][0])

    def test_non_accetta_alias_ambiguo_o_dialogo_incompleto(self):
        self.chat['conversazione'][0]['text'] = 'Altro contenuto'
        with self.assertRaises(ValueError): prepara_chat(self.chat, self.scheda)
        self.chat['conversazione'][0].pop('text')
        self.chat['conversazione'].pop()
        with self.assertRaises(ValueError): prepara_chat(self.chat, self.scheda)

    def test_chiusura_utente_e_messaggio_vuoto(self):
        self.chat['conversazione'].append({'sender': 'Utente', 'testo': 'Va bene.'})
        result = prepara_chat(self.chat, self.scheda)
        self.assertTrue(result['validazione']['chiusura_utente'])
        self.assertEqual(result['validazione']['scambi_effettivi'], 1)
        self.assertEqual(result['validazione']['messaggi_totali'], 3)
        self.chat['conversazione'][1]['testo'] = ''
        with self.assertRaises(ValueError): prepara_chat(self.chat, self.scheda)

    def test_recupera_solo_vuoto_interno_ridondante(self):
        self.chat['conversazione'].insert(1, {'sender': 'Agente', 'text': ''})
        r = prepara_chat(self.chat, self.scheda)
        self.assertEqual(r['stato'], 'valido')
        self.assertEqual(len(r['chat']['conversazione']), 2)
        self.chat['conversazione'].append({'sender': 'Utente', 'testo': ''})
        with self.assertRaises(ValueError): prepara_chat(self.chat, self.scheda)

    def test_stato_citato_solo_nella_domanda_non_e_confermato(self):
        self.chat['metadati']['descrizione'] = 'Questionario in compilazione'
        self.chat['conversazione'][1]['testo'] = 'È in compilazione o in bozza?'
        r = prepara_chat(self.chat, self.scheda)
        self.assertEqual(r['stato'], 'da_verificare')
        self.chat['conversazione'].append({'sender': 'Utente', 'testo': 'È in compilazione.'})
        self.assertEqual(prepara_chat(self.chat, self.scheda)['stato'], 'valido')

    def test_schema_messaggio_conversazione(self):
        self.entita['tipo'] = 'PERSON'
        self.entita['sostituzione'] = '[PERSON_1]'
        self.entita['id_entita'] = 'persona_1'
        self.entita['id_forma'] = 'completa'
        self.scheda['schema_output'] = 'chat_v5'
        self.scheda['riferimenti_detection'] = [{
            'reference_id':'persona_1', 'riferimento':'{{persona_1}}', 'tipo':'PERSONA'}]
        self.chat.pop('trattamento_atteso')
        self.chat['conversazione'].extend([
            {'sender': 'Utente', 'testo': 'Il problema continua.'},
            {'sender': 'Agente', 'testo': 'Che cosa accade?'},
            {'sender': 'Utente', 'testo': 'Non riesco ad accedere.'},
            {'sender': 'Agente', 'testo': 'La richiesta va verificata.'},
        ])
        result = prepara_chat(self.chat, self.scheda)
        self.assertEqual(result['chat']['conversazione'][0]['testo'], 'Sono Anna Rossi')
        self.assertEqual(result['detection_attesa'][0]['text'], 'Anna Rossi')

    def test_chat_v5_richiede_almeno_tre_scambi(self):
        self.entita['tipo'] = 'PERSON'
        self.entita['sostituzione'] = '[PERSON_1]'
        self.entita['id_entita'] = 'persona_1'
        self.entita['id_forma'] = 'completa'
        self.scheda['schema_output'] = 'chat_v5'
        self.scheda['numero_scambi'] = 4
        self.scheda['riferimenti_detection'] = [{
            'reference_id':'persona_1', 'riferimento':'{{persona_1}}', 'tipo':'PERSON'}]
        self.chat.pop('trattamento_atteso')
        with self.assertRaisesRegex(ValueError, 'almeno 3 scambi'):
            prepara_chat(self.chat, self.scheda)

if __name__ == '__main__': unittest.main()
