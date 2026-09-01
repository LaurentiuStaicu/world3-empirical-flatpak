import json
import unittest

from world3_empirical.sources.world_bank import build_url, parse_world_bank_payload


class WorldBankTests(unittest.TestCase):
    def test_parser_drops_nulls_and_sorts_years(self):
        payload = [
            {"page": 1},
            [
                {"date": "2024", "value": 12, "countryiso3code": "WLD"},
                {"date": "2023", "value": None, "countryiso3code": "WLD"},
                {"date": "2022", "value": 10, "countryiso3code": "WLD"},
            ],
        ]
        frame = parse_world_bank_payload(json.dumps(payload), "TEST")
        self.assertEqual(frame["year"].tolist(), [2022, 2024])
        self.assertEqual(frame["value"].tolist(), [10.0, 12.0])

    def test_url_is_explicitly_global(self):
        self.assertIn("/country/WLD/indicator/SP.POP.TOTL", build_url("SP.POP.TOTL"))


if __name__ == "__main__":
    unittest.main()

