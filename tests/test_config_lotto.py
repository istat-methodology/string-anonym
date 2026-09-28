import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from lotto import comando


class ConfigLottoTest(unittest.TestCase):
    def test_fasi_e_controllo_senza_api(self):
        with tempfile.TemporaryDirectory() as directory:
            prompts = Path(directory) / 'prompts.jsonl'
            prompts.write_text('\n'.join(json.dumps({'seed': 100}) for _ in range(2)))
            config = dict(catalogo='config/scenari_mirati_v4_3.json', totale=2,
                          seed=100, prompts=str(prompts), output=directory+'/risposte',
                          deployment='gpt-5.6-terra')
            self.assertIn('--totale', comando(config, 'prepara'))
            self.assertIn('--solo-controllo', comando(config, 'controlla'))
            self.assertNotIn('--solo-controllo', comando(config, 'genera'))
            with self.assertRaises(ValueError):
                comando({**config, 'totale': 4}, 'genera')
            with self.assertRaises(ValueError):
                comando({**config, 'seed': 101}, 'genera')
            with self.assertRaises(ValueError):
                comando({**config, 'totale': 3}, 'prepara')
            with self.assertRaises(ValueError):
                comando({**config, 'api_key': 'non-ammesso'}, 'prepara')
