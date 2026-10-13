import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esporta_dataset_detection import converti, esporta, espandi_address
from esporta_dataset_masking import leggi


class DetectionExportTest(unittest.TestCase):
    def setUp(self):
        self.record = {
            "id": "caso", "stato": "valido", "prompt": {"ipotesi_policy": ["segreto"]},
            "chat": {"metadati": {"descrizione": "Anna a Roma"}, "conversazione": [
                {"sender": "Utente", "testo": "Anna cerca Roma"},
                {"sender": "Agente", "testo": "Quale periodo?"},
            ]},
            "detection_attesa": [
                {"detection_id": "det_1", "field": "conversazione.0.testo",
                 "start": 0, "end": 4, "text": "Anna", "type": "PERSON",
                 "sources": [{"detector": "synthetic_slot"}],
                 "metadata": {"reference_id": "persona_1"}},
                {"detection_id": "det_2", "field": "conversazione.0.testo",
                 "start": 11, "end": 15, "text": "Roma", "type": "LOCATION",
                 "sources": [{"detector": "synthetic_reference"}],
                 "metadata": {"reference_id": "comune"}},
            ],
        }

    def test_separa_input_gold_e_adattatore(self):
        original = copy.deepcopy(self.record)
        inp, gold, adapter = converti(self.record, "id")
        self.assertEqual(set(inp), {"id", "conversazione"})
        self.assertNotIn("prompt", json.dumps(inp))
        self.assertEqual([d["type"] for d in gold["detections"]], ["PERSON", "LOCATION"])
        self.assertEqual([a["tipo"] for a in adapter["annotazioni"]], ["PERSON", "LOCATION"])
        self.assertEqual(self.record, original)

    def test_rifiuta_offset_id_e_stato(self):
        for modifica in ("offset", "id", "stato"):
            record = copy.deepcopy(self.record)
            if modifica == "offset": record["detection_attesa"][0]["end"] = 3
            if modifica == "id": record["detection_attesa"][1]["detection_id"] = "det_1"
            if modifica == "stato": record["stato"] = "da_verificare"
            with self.subTest(modifica=modifica), self.assertRaises(ValueError):
                converti(record, "id")

    def test_gold_canonico_ammette_overlap_ed_espande_address(self):
        record = copy.deepcopy(self.record)
        record["chat"]["conversazione"][0]["testo"] = "Scrivo da Via Roma 12, Alfa"
        record["detection_attesa"] = [{
            "detection_id": "det_address", "field": "conversazione.0.testo",
            "start": 10, "end": 27, "text": "Via Roma 12, Alfa", "type": "ADDRESS",
            "sources": [{"detector": "synthetic_slot"}],
        }]
        _, gold, legacy = converti(record, "id", {"Alfa"})
        self.assertEqual([(d["type"], d["text"]) for d in gold["detections"]], [
            ("LOCATION", "Via Roma 12"),
            ("ADDRESS", "Via Roma 12, Alfa"),
            ("LOCATION", "Alfa"),
        ])
        self.assertEqual([(a["tipo"], a["testo"]) for a in legacy["annotazioni"]],
                         [("ADDRESS", "Via Roma 12, Alfa")])

    def test_manifest_e_nessuna_sovrascrittura(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            source.write_text(json.dumps(self.record) + "\n", encoding="utf-8")
            manifest = esporta([source], root / "out")
            self.assertEqual(manifest["detection_attese"], 2)
            self.assertEqual(manifest["categorie"], {"LOCATION": 1, "PERSON": 1})
            self.assertEqual(len(leggi(root / "out/input.jsonl")), 1)
            self.assertEqual(len(leggi(root / "out/detections_attese.jsonl")), 1)
            self.assertEqual(len(leggi(root / "out/annotazioni_ner_attese.jsonl")), 1)
            with self.assertRaises(ValueError):
                esporta([source], root / "out")


if __name__ == "__main__":
    unittest.main()
