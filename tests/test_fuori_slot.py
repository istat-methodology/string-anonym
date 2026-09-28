import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from validazione import prepara_chat, controlla_identificativi_fuori_slot
from rivalida_chat import rivalida


class FuoriSlotTest(unittest.TestCase):
    def setUp(self):
        self.scheda={'modalita':'senza_dati_personali','metadati_fissati':{'data_sintetica':'2026-04-01','chiave_indagine':None},'entita_previste':[],'numero_scambi':1}
        self.chat={'metadati':{**self.scheda['metadati_fissati'],'descrizione':'Richiesta sulla pratica precedente.'},'conversazione':[{'sender':'Utente','testo':'Cerco la ricevuta.'},{'sender':'Agente','testo':'A quale richiesta si riferisce?'}],'trattamento_atteso':{'mascherare':[],'conservare':[],'motivazione':'Nessuna entità prevista.'}}

    def test_formati_contestuali(self):
        for testo, valore in [('Prot.n. 45821','45821'),('PROT. N. 1589563/25','1589563/25'),('protocollo n° 00123/26','00123/26'),('pratica: 12345','12345'),('ticket numero 01234','01234')]:
            self.chat['conversazione'][0]['testo']=testo
            with self.subTest(testo=testo):
                result=prepara_chat(self.chat,self.scheda)
                self.assertEqual(result['stato'],'da_verificare')
                self.assertEqual(result['validazione']['identificativi_fuori_slot'][0]['testo'],valore)
                self.assertEqual(result['chat']['trattamento_atteso']['mascherare'],[])

    def test_tutti_i_campi_e_conservazione_originale(self):
        self.chat['conversazione'][1]['testo']='Prot. n. 45821'
        self.chat['metadati']['descrizione']='Pratica 45821'
        self.chat['trattamento_atteso']['conservare']=['Protocollo 45821']
        self.chat['trattamento_atteso']['motivazione']='Ticket 45821'
        record={'stato':'valido','prompt':{'scheda':self.scheda},'risposta_originale':{'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(self.chat)}]}]}}
        original=copy.deepcopy(record);result=rivalida(record)
        self.assertEqual(result['stato'],'da_verificare')
        self.assertEqual(len(result['validazione']['identificativi_fuori_slot']),4)
        self.assertEqual(result['risposta_originale'],original['risposta_originale'])
        self.assertEqual(record,original)

    def test_slot_e_riferimenti_pubblici_non_segnalati(self):
        self.chat['conversazione'][0]['testo']='Prot. n. {{num_pratica_1}}, nel 2025. Indagine IST-00070, anno 2024, 45821 abitanti.'
        self.assertEqual(controlla_identificativi_fuori_slot(self.chat),[])
        e={'segnaposto':'{{num_pratica_1}}','tipo':'NUM_PRATICA','valore_proposto':'1589563/25','id_entita':'num_pratica_1','sostituzione':'[NUM_PRATICA_1]'}
        self.scheda.update(modalita='con_dati_personali',entita_previste=[e])
        self.chat['trattamento_atteso']['mascherare']=[{k:e[k] for k in ('segnaposto','tipo','sostituzione')}]
        self.assertEqual(prepara_chat(self.chat,self.scheda)['stato'],'valido')
        self.chat['conversazione'][1]['testo']='Anche la pratica 99999?'
        self.assertEqual(prepara_chat(self.chat,self.scheda)['stato'],'da_verificare')


if __name__=='__main__':unittest.main()
