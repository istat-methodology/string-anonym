from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from detection import merge_detection


class DetectionTest(unittest.TestCase):
    def setUp(self):
        self.fields = {'conversazione.0.testo': 'Sono Anna e abito a Roma.'}

    def detection(self, start, end, tipo, detector, **source):
        text = self.fields['conversazione.0.testo']
        return {'field': 'conversazione.0.testo', 'start': start, 'end': end,
                'text': text[start:end], 'type': tipo,
                'sources': [{'detector': detector, **source}]}

    def test_merge_unisce_coincidenze_e_fonti(self):
        detections = [self.detection(5, 9, 'PERSON', 'ner', score=0.9),
                      self.detection(5, 9, 'PERSON', 'gazetteer')]
        result = merge_detection(detections, self.fields, 'record-1')
        self.assertEqual(len(result), 1)
        self.assertEqual({s['detector'] for s in result[0]['sources']}, {'ner', 'gazetteer'})
        self.assertTrue(result[0]['detection_id'].startswith('det_'))

    def test_merge_conserva_sovrapposizioni_e_disaccordi(self):
        detections = [self.detection(19, 23, 'LOCATION', 'ner'),
                      self.detection(11, 23, 'ADDRESS', 'ner'),
                      self.detection(19, 23, 'ADDRESS', 'regex')]
        result = merge_detection(detections, self.fields)
        self.assertEqual(len(result), 3)
        self.assertEqual({d['type'] for d in result if d['start'] == 19},
                         {'LOCATION', 'ADDRESS'})

    def test_merge_valida_offset_testo_tipo_e_sorgente(self):
        invalid = self.detection(5, 9, 'PERSON', 'ner')
        for change in ({'text': 'Elsa'}, {'end': 99}, {'type': 'UNKNOWN'}, {'sources': []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                merge_detection([{**invalid, **change}], self.fields)


if __name__ == '__main__':
    unittest.main()
