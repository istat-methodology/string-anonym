import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from genera_chat import scegli_provider, endpoint_provider, parametri_richiesta, estrai_testo
from rivalida_chat import rivalida


class ProviderTest(unittest.TestCase):
    def test_routing_ed_endpoint(self):
        self.assertEqual(scegli_provider('claude-sonnet-5'), 'anthropic')
        self.assertEqual(scegli_provider('gpt-5.6-terra'), 'openai')
        self.assertEqual(scegli_provider('nome-personalizzato', 'anthropic'), 'anthropic')
        with patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://prova.services.ai.azure.com/openai/v1/'}, clear=True):
            self.assertEqual(endpoint_provider('anthropic'), 'https://prova.services.ai.azure.com/anthropic/')
            self.assertEqual(endpoint_provider('openai'), 'https://prova.services.ai.azure.com/openai/v1/')
            self.assertEqual(endpoint_provider('anthropic','https://altro/anthropic'), 'https://altro/anthropic/')
        with patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://altro.example/v1'}, clear=True):
            with self.assertRaises(ValueError): endpoint_provider('anthropic')

    def test_parametri_non_modificano_prompt(self):
        prompt = {'messages':[{'role':'system','content':'Solo JSON'},{'role':'user','content':'Scheda'}]}
        originale = copy.deepcopy(prompt)
        a = parametri_richiesta(prompt,'claude-sonnet-5',6000,'anthropic')
        self.assertEqual(a, {'model':'claude-sonnet-5','system':'Solo JSON','messages':[{'role':'user','content':'Scheda'}],'max_tokens':6000})
        o = parametri_richiesta(prompt,'gpt-5.6-terra',6000,'openai')
        self.assertEqual(o['input'],prompt['messages'])
        self.assertFalse(o['store'])
        self.assertEqual(prompt,originale)

    def test_risposte_complete_troncate_e_vuote(self):
        risposta = {'stop_reason':'end_turn','content':[{'type':'thinking','thinking':'Privato'},{'type':'text','text':'{"ok": true}'}]}
        self.assertEqual(json.loads(estrai_testo(risposta,'anthropic')), {'ok':True})
        for motivo in ['max_tokens','refusal','tool_use','pause_turn',None]:
            with self.subTest(motivo=motivo), self.assertRaises(ValueError):
                estrai_testo({**risposta,'stop_reason':motivo},'anthropic')
        with self.assertRaises(ValueError): estrai_testo({'stop_reason':'end_turn','content':[]},'anthropic')
        with self.assertRaises(ValueError): estrai_testo({'status':'incomplete','output':[]})

    def test_rivalidazione_entrambi_provider_e_legacy(self):
        scheda = {'modalita':'senza_dati_personali','metadati_fissati':{'data_sintetica':'2026-09-27','chiave_indagine':None},'entita_previste':[],'numero_scambi':1}
        chat = {'metadati':{**scheda['metadati_fissati'],'descrizione':'Ricerca dati'},'conversazione':[{'sender':'Utente','testo':'Cerco dati.'},{'sender':'Agente','testo':'Per quale periodo?'}],'trattamento_atteso':{'mascherare':[],'conservare':[],'motivazione':'Nessuna entità.'}}
        testo = json.dumps(chat)
        for provider in ['anthropic','openai',None]:
            risposta = ({'stop_reason':'end_turn','content':[{'type':'text','text':testo}]} if provider=='anthropic' else {'status':'completed','output':[{'content':[{'type':'output_text','text':testo}]}]})
            record = {'prompt':{'scheda':scheda},'risposta_originale':risposta}
            if provider: record['provider']=provider
            risultato = rivalida(record)
            self.assertEqual(risultato['stato'],'valido')
            self.assertEqual(risultato['risposta_originale'],risposta)
        record={'provider':'anthropic','prompt':{'scheda':scheda},'risposta_originale':{'stop_reason':'max_tokens','content':[{'type':'text','text':testo}]}}
        self.assertEqual(rivalida(record)['stato'],'da_verificare')


if __name__ == '__main__': unittest.main()
