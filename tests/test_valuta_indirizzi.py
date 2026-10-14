import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from valuta_indirizzi import valuta


class AddressEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.text = "Scrivo da Via Angelo Lauri 96, Anzio oggi"
        self.identifier = "case"
        self.inputs = [{"id": self.identifier, "conversazione": [
            {"sender": "Utente", "testo": self.text}
        ]}]
        start = self.text.index("Via Angelo")
        city_start = self.text.index("Anzio")
        full = "Via Angelo Lauri 96, Anzio"
        self.gold = [{"id": self.identifier, "detections": [
            {"detection_id": "address", "field": "conversazione.0.testo",
             "start": start, "end": start + len(full), "text": full, "type": "ADDRESS",
             "sources": [{"detector": "synthetic_slot"}]},
            {"detection_id": "street", "field": "conversazione.0.testo",
             "start": start, "end": start + len("Via Angelo Lauri 96"),
             "text": "Via Angelo Lauri 96", "type": "LOCATION",
             "sources": [{"detector": "synthetic_address_component",
                          "component": "street_civic", "parent_detection_id": "address"}]},
            {"detection_id": "city", "field": "conversazione.0.testo",
             "start": city_start, "end": city_start + 5, "text": "Anzio", "type": "LOCATION",
             "sources": [{"detector": "synthetic_address_component",
                          "component": "municipality", "parent_detection_id": "address"}]},
        ]}]

    def prediction(self, spans):
        return [{"id": self.identifier, "stato": "ok", "annotazioni": [
            {"campo": "conversazione.0.testo", "start": self.text.index(value),
             "end": self.text.index(value) + len(value), "tipo": "LOCATION", "testo": value}
            for value in spans
        ]}]

    def test_indirizzo_completo_in_due_span(self):
        report = valuta(self.inputs, self.gold,
                        self.prediction(["Via Angelo Lauri 96", "Anzio"]))
        self.assertEqual(report["full_address"]["complete_rate"], 1)
        self.assertEqual(report["outcomes"], {"complete": 1})
        self.assertEqual(report["details"][0]["residual_text"], "")

    def test_confine_parziale_ottiene_credito_ma_non_completezza(self):
        report = valuta(self.inputs, self.gold,
                        self.prediction(["Angelo Lauri 96", "Anzio"]))
        self.assertGreater(report["full_address"]["character_coverage"], 0.8)
        self.assertEqual(report["full_address"]["complete_rate"], 0)
        self.assertEqual(report["outcomes"], {"partial_other": 1})
        self.assertEqual(report["details"][0]["residual_text"], "Via")

    def test_comune_solo_segnala_strada_e_civico_esposti(self):
        report = valuta(self.inputs, self.gold, self.prediction(["Anzio"]))
        self.assertEqual(report["outcomes"], {"municipality_only": 1})
        self.assertEqual(report["components"]["municipality"]["complete_rate"], 1)
        self.assertEqual(report["components"]["street"]["complete_rate"], 0)
        self.assertEqual(report["components"]["house_number"]["complete_rate"], 0)

    def test_civico_esposto(self):
        report = valuta(self.inputs, self.gold,
                        self.prediction(["Via Angelo Lauri", "Anzio"]))
        self.assertEqual(report["outcomes"], {"house_number_exposed": 1})
        self.assertEqual(report["details"][0]["residual_text"], "96")

    def test_componenti_strutturate_opzionali_con_interno(self):
        text = "Sede: Angelo Lauri 96, interno 4"
        start = text.index("Angelo")
        value = "Angelo Lauri 96, interno 4"
        inputs = [{"id": "structured", "conversazione": [
            {"sender": "Utente", "testo": text}
        ]}]
        components = {
            "street_name": {"start": start, "end": start + 12, "text": "Angelo Lauri"},
            "house_number": {"start": start + 13, "end": start + 15, "text": "96"},
            "internal": {"start": start + 17, "end": start + 26, "text": "interno 4"},
        }
        gold = [{"id": "structured", "detections": [{
            "detection_id": "address", "field": "conversazione.0.testo",
            "start": start, "end": start + len(value), "text": value, "type": "ADDRESS",
            "sources": [{"detector": "synthetic_slot"}],
            "metadata": {"address_variant": "with_internal",
                         "address_components": components},
        }]}]
        predictions = [{"id": "structured", "stato": "ok", "annotazioni": [{
            "campo": "conversazione.0.testo", "start": start,
            "end": start + len(value), "tipo": "LOCATION", "testo": value,
        }]}]
        report = valuta(inputs, gold, predictions)
        self.assertEqual(report["outcomes"], {"complete": 1})
        self.assertEqual(report["components"]["internal"]["complete_rate"], 1)
        self.assertEqual(report["components"]["municipality"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
