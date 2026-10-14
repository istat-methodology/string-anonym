import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bootstrap_metriche import bootstrap, percentile


class BootstrapMetricheTest(unittest.TestCase):
    def setUp(self):
        text_a = "Sono Ada a Via Roma 1, Tivoli"
        text_b = "Nessun dato"
        self.inputs = [
            {"id": "a", "conversazione": [{"sender": "Utente", "testo": text_a}]},
            {"id": "b", "conversazione": [{"sender": "Utente", "testo": text_b}]},
        ]
        person_start = text_a.index("Ada")
        street_start = text_a.index("Via Roma")
        city_start = text_a.index("Tivoli")
        self.expected = [
            {"id": "a", "annotazioni": [
                {"campo": "conversazione.0.testo", "start": person_start,
                 "end": person_start + 3, "tipo": "PERSON", "testo": "Ada"},
                {"campo": "conversazione.0.testo", "start": street_start,
                 "end": street_start + 10, "tipo": "LOCATION", "testo": "Via Roma 1"},
                {"campo": "conversazione.0.testo", "start": city_start,
                 "end": city_start + 6, "tipo": "LOCATION", "testo": "Tivoli"},
            ]},
            {"id": "b", "annotazioni": []},
        ]
        full = "Via Roma 1, Tivoli"
        self.gold_addresses = [
            {"id": "a", "detections": [{
                "detection_id": "address", "field": "conversazione.0.testo",
                "start": street_start, "end": street_start + len(full),
                "text": full, "type": "ADDRESS", "sources": [],
                "metadata": {"address_components": {
                    "street_type": {"start": street_start, "end": street_start + 3,
                                    "text": "Via"},
                    "street_name": {"start": street_start + 4, "end": street_start + 8,
                                    "text": "Roma"},
                    "house_number": {"start": street_start + 9, "end": street_start + 10,
                                     "text": "1"},
                    "municipality": {"start": city_start, "end": city_start + 6,
                                     "text": "Tivoli"},
                }},
            }]},
            {"id": "b", "detections": []},
        ]
        annotations = self.expected[0]["annotazioni"]
        predictions = [
            {"id": "a", "stato": "ok", "annotazioni": annotations},
            {"id": "b", "stato": "ok", "annotazioni": []},
        ]
        self.predictions = {"first": predictions, "second": predictions}

    def test_percentile_interpola(self):
        self.assertEqual(percentile([0, 10], 0.25), 2.5)

    def test_bootstrap_appaiato_identico_ha_delta_zero(self):
        report = bootstrap(self.inputs, self.expected, self.gold_addresses,
                           self.predictions, replicates=100, seed=7)
        self.assertEqual(report["models"]["first"]["point"]["micro"]["f1"], 1)
        self.assertEqual(report["models"]["first"]["point"]["address"]["complete_rate"], 1)
        deltas = report["paired_differences"]
        self.assertTrue(deltas)
        self.assertTrue(all(item["estimate"] == 0 for item in deltas))
        self.assertTrue(all(item["ci_lower"] == item["ci_upper"] == 0 for item in deltas))


if __name__ == "__main__":
    unittest.main()
