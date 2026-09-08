import json
import unittest

from world3_empirical.sources.unido import parse_data, parse_metadata, request_payload


class UnidoDataTests(unittest.TestCase):
    def metadata(self):
        return {
            "id": 140,
            "name": "National Accounts Database",
            "countries": [],
            "groups": [{"c": "WORLD", "lang": {"en": "World"}}],
            "periods": ["2024", "2025"],
            "variables": [
                {"c": "MvaCod", "lang": {"en": "MVA, constant USD"}},
                {"c": "Pop", "lang": {"en": "Population"}},
            ],
        }

    def test_request_uses_dynamic_dataset_id_and_world_group(self):
        payload = request_payload(parse_metadata(self.metadata()))
        self.assertEqual(payload["datasetId"], 140)
        self.assertEqual(payload["countryCode"], "WORLD")
        self.assertEqual(payload["periods"], ["2024", "2025"])

    def test_parser_rejects_duplicate_observations(self):
        payload = {
            "data": [
                {"p": "2025", "c": "MvaCod", "v": 1.0},
                {"p": "2025", "c": "MvaCod", "v": 2.0},
                {"p": "2025", "c": "Pop", "v": 3.0},
            ],
            "ym": [],
        }
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_data(json.dumps(payload))

    def test_parser_preserves_year_metadata(self):
        payload = {
            "data": [
                {"p": "2025", "c": "MvaCod", "v": 10.0},
                {"p": "2025", "c": "Pop", "v": 2.0},
            ],
            "ym": [{"year": "2025", "metadataList": [{"note": "UNIDO estimate"}]}],
        }
        frame, metadata = parse_data(payload)
        self.assertEqual(len(frame), 2)
        self.assertEqual(metadata[0]["year"], "2025")


if __name__ == "__main__":
    unittest.main()
