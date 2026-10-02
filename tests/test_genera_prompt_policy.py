import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genera_prompt_policy import genera, valida_risposta_policy


class PolicyPromptTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] /
                                  'config/policy_conversation_draft_2.json').read_text())
        self.record = {'id':'x', 'stato':'valido',
            'chat':{'conversazione':[{'sender':'Utente','testo':'Cerco Roma'}]},
            'detection_attesa':[{'detection_id':'det_1','field':'conversazione.0.testo',
                'start':6,'end':10,'text':'Roma','type':'LOCATION',
                'metadata':{'reference_id':'comune'}}],
            'prompt':{'ipotesi_policy':[{'reference_id':'comune','ipotesi_iniziale':'KEEP',
                                        'stato':'APPROVED'}]}}

    def test_gold_separato_dal_messaggio(self):
        row = list(genera([self.record], self.config))[0]
        self.assertEqual(row['attese_policy'][0]['expected_action'], 'KEEP')
        user = json.loads(row['messages'][1]['content'])
        self.assertNotIn('attese_policy', user)
        self.assertNotIn('expected_action', row['messages'][1]['content'])
        self.assertIn('esperimento separato', row['messages'][0]['content'])

    def test_validazione_risposta(self):
        value={'decisions':[{'detection_id':'det_1','action':'KEEP',
                            'replacement':None,'reason':'Territorio statistico.'}]}
        valida_risposta_policy(value, ['det_1'])
        value['decisions'][0]['replacement']='Roma'
        with self.assertRaises(ValueError):
            valida_risposta_policy(value, ['det_1'])

    def test_mask_richiede_placeholder_neutro_del_tipo(self):
        detections = [{'detection_id':'det_1', 'text':'Mario Rossi', 'type':'PERSON'}]
        value = {'decisions':[{'detection_id':'det_1', 'action':'MASK',
                               'replacement':'[PERSON_1]', 'reason':'Nome personale.'}]}
        valida_risposta_policy(value, detections)
        value['decisions'][0]['replacement'] = '[NOME RICHIEDENTE]'
        with self.assertRaisesRegex(ValueError, 'Placeholder MASK'):
            valida_risposta_policy(value, detections)


if __name__ == '__main__':
    unittest.main()
