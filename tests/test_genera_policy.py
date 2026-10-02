import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from genera_policy import prepara_risposta_policy


class PolicyRunnerTest(unittest.TestCase):
    def setUp(self):
        policy_input = {"detections": [{"detection_id": "det_1", "text": "Roma",
                                         "type": "LOCATION"}]}
        self.prompt = {
            "attese_policy": [{"detection_id": "det_1"}],
            "messages": [{"role": "system", "content": "Policy"},
                         {"role": "user", "content": json.dumps(policy_input)}],
        }
        self.value = {
            "decisions": [{"detection_id": "det_1", "action": "KEEP",
                           "replacement": None, "reason": "Riferimento pubblico."}],
        }

    def test_json_puro_e_cornice(self):
        text = json.dumps(self.value)
        value, corrections = prepara_risposta_policy(text, self.prompt)
        self.assertEqual(value, self.value)
        self.assertEqual(corrections, [])
        value, corrections = prepara_risposta_policy(f"```json\n{text}\n```", self.prompt)
        self.assertEqual(value, self.value)
        self.assertTrue(corrections)

    def test_rifiuta_decisioni_incomplete(self):
        self.value["decisions"] = []
        with self.assertRaises(ValueError):
            prepara_risposta_policy(json.dumps(self.value), self.prompt)


if __name__ == "__main__":
    unittest.main()
