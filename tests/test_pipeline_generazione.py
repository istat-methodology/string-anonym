import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pipeline_generazione import comando


class PipelineGenerazioneTest(unittest.TestCase):
    def test_fasi_e_controllo_senza_api(self):
        with tempfile.TemporaryDirectory() as directory:
            prompts = Path(directory) / 'prompts.jsonl'
            sorgente = Path(__file__).resolve().parents[1] / 'config/scenari.json'
            provenienza = {'sha256_file': {'scenari.json': hashlib.sha256(sorgente.read_bytes()).hexdigest()}}
            record = {'seed': 100, 'versione_prompt': 'test-1', 'provenienza_locale': provenienza}
            prompts.write_text('\n'.join(json.dumps(record) for _ in range(2)))
            config = dict(catalogo='config/scenari.json', totale=2,
                          seed=100, prompts=str(prompts), output=directory+'/risposte',
                          deployment='gpt-5.6-terra', versione_prompt='test-1')
            self.assertIn('--totale', comando(config, 'prepara'))
            self.assertIn('--solo-controllo', comando(config, 'controlla'))
            self.assertNotIn('--solo-controllo', comando(config, 'genera'))
            self.assertIn('--riprendi', comando(config, 'riprendi'))
            with self.assertRaises(ValueError):
                comando({**config, 'totale': 4}, 'genera')
            with self.assertRaises(ValueError):
                comando({**config, 'seed': 101}, 'genera')
            with self.assertRaises(ValueError):
                comando({**config, 'versione_prompt': 'test-2'}, 'genera')
            with self.assertRaises(ValueError):
                comando({**config, 'totale': 3}, 'prepara')
            with self.assertRaises(ValueError):
                comando({**config, 'api_key': 'non-ammesso'}, 'prepara')

            planned = {**config, 'piano': 'config/piano_dataset_paper_300.json'}
            prepared = comando(planned, 'prepara')
            self.assertIn('--piano', prepared)
            self.assertNotIn('--totale', prepared)
