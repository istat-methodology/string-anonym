import copy
import csv
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from annotazioni import sostituisci_con_span, valida_span
from genera_valori import carica_regole, genera_codice
from parse_input import carica_input, leggi_indagini
from validazione import prepara_chat


class InputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'nomi.txt').write_text('\ufeffAnna\nAnna\n')
        (self.root / 'cognomi.txt').write_text('Rossi\n')
        self.write('codici_comuni.csv', ['Codice Comune (alfanumerico)', 'Comune', 'Codice catasto'], [['001001', 'Alfa', 'A001']])
        self.write('strade_lazio.csv', ['CODICE_ISTAT', 'COMUNE', 'ODONIMO'], [['001001', 'Alfa', 'VIA ROMA']]*2)
        self.write('codici_psn.csv', ['codice_psn', 'nome_indagine', 'tipo_rispondente'], [['IST-00001', 'Prova', 'imprese']]*2)

    def write(self, name, headers, rows):
        with (self.root / name).open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f, delimiter=';'); w.writerow(headers); w.writerows(rows)

    def test_solo_compatto_deduplica_e_zeri(self):
        dati = carica_input(self.root)
        self.assertEqual(dati.strade, [('001001', 'VIA ROMA')])
        self.assertEqual(dati.codici_catastali, {'001001': 'A001'})
        self.assertEqual(len(dati.indagini), 1)
        self.assertEqual(dati.nomi, ['Anna'])
        self.assertFalse((self.root / 'indirizzi_lazio.csv').exists())

    def test_rifiuta_conflitti_e_valori_mancanti(self):
        for comune in ['Beta', '']:
            self.write('strade_lazio.csv', ['CODICE_ISTAT','COMUNE','ODONIMO'], [['001001', comune, 'VIA ROMA']])
            with self.assertRaises(ValueError): carica_input(self.root)
        self.write('codici_psn.csv', ['codice_psn','nome_indagine','tipo_rispondente'], [['IST-00001','A','imprese'], ['IST-00001','B','imprese']])
        with self.assertRaises(ValueError): leggi_indagini(self.root / 'codici_psn.csv')


class RegoleTest(unittest.TestCase):
    def test_formati_seed_e_configurazione(self):
        regole = carica_regole()
        def lotto():
            rng = random.Random(42)
            return [genera_codice(t, rng, regole) for _ in range(30) for t in ('COD_UTENTE','NUM_PRATICA','PASSWORD','PHONE')]
        self.assertEqual(lotto(), lotto())
        for i, valore in enumerate(lotto()):
            if i % 4 == 0: self.assertRegex(valore, r'^(P0\d{8}|QOL\d{7}|\d{9})$')
            if i % 4 == 1: self.assertRegex(valore, r'^\d{7}/(25|26)$')
            if i % 4 == 2: self.assertIn(len(valore), [8,10,12])
            if i % 4 == 3: self.assertRegex(valore, r'^(\+39 )?3\d{2}[ .]?\d{3}[ .]?\d{4}$')
        regole['COD_UTENTE']['varianti'] = [{'prefisso':'XYZ','cifre':5}]
        self.assertRegex(genera_codice('COD_UTENTE', random.Random(0), regole), r'^XYZ\d{5}$')
        with self.assertRaises(ValueError): genera_codice('COD_UNITA', random.Random(0), regole)


class SpanTest(unittest.TestCase):
    def setUp(self):
        self.e = {'id_entita':'persona_1','id_forma':'completa','tipo':'PERSON','segnaposto':'{{persona_1}}','valore_proposto':'Anna D’Angelo','sostituzione':'[PERSON_1]'}

    def test_unicode_ripetizioni_forme_e_confini(self):
        breve = {**self.e, 'id_forma':'cognome', 'segnaposto':'{{cognome_1}}', 'valore_proposto':'D’Angelo'}
        testo, spans = sostituisci_con_span('🙂 È {{persona_1}}; {{cognome_1}}. {{persona_1}}', [self.e,breve], 'conversazione.0.testo')
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0]['start'], 4)
        self.assertEqual({s['id_entita'] for s in spans}, {'persona_1'})
        for s in spans: self.assertEqual(testo[s['start']:s['end']], s['testo'])
        with self.assertRaises(ValueError): valida_span(testo, [spans[0], spans[0]])
        for testo_errato in ['{{sconosciuto}}', '{{persona_1}', '{{persona_1}}}}']:
            with self.assertRaises(ValueError): sostituisci_con_span(testo_errato, [self.e], 'campo')

    def test_intera_chat_e_descrizione(self):
        scheda = {'modalita':'con_dati_personali','metadati_fissati':{'data_sintetica':'2026-09-27','chiave_indagine':None},'entita_previste':[self.e],'numero_scambi':1}
        chat = {'metadati':{**scheda['metadati_fissati'],'descrizione':'Richiesta di {{persona_1}}'},'conversazione':[{'sender':'Utente','testo':'Sono {{persona_1}}'},{'sender':'Agente','testo':'{{persona_1}}, quale dato cerca?'}], 'trattamento_atteso':{'mascherare':[{k:self.e[k] for k in ('segnaposto','tipo','sostituzione')}],'conservare':['Roma come territorio'],'motivazione':'{{persona_1}} si identifica'}}
        risultato = prepara_chat(chat, scheda)
        spans = risultato['chat']['trattamento_atteso']['mascherare']
        self.assertEqual(len(spans), 4)
        self.assertEqual(risultato['stato'],'valido')
        self.assertIn('{{persona_1}}', chat['metadati']['descrizione'])
        for span in spans:
            value = risultato['chat']
            for key in span['campo'].split('.'):
                value = value[int(key)] if isinstance(value,list) else value[key]
            self.assertEqual(value[span['start']:span['end']],span['testo'])
        scheda['modalita']='senza_dati_personali'
        with self.assertRaises(ValueError): prepara_chat(chat, scheda)

    def test_prefisso_protocollo_escluso(self):
        e = {**self.e,'tipo':'NUM_PRATICA','valore_proposto':'1589563/25'}
        testo, spans = sostituisci_con_span('Prot.n. {{persona_1}}', [e], 'campo')
        self.assertEqual(testo[spans[0]['start']:spans[0]['end']], '1589563/25')
        self.assertEqual(spans[0]['start'],8)


if __name__ == '__main__': unittest.main()
