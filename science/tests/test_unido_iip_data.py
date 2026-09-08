import unittest

import pandas as pd

from world3_empirical.sources.unido_iip import (
    aggregate_balanced_panel,
    parse_iip_export,
    parse_metadata,
    parse_mva_weights,
)


class UnidoIipDataTests(unittest.TestCase):
    def test_metadata_requires_original_index(self):
        metadata = {
            "id": 166,
            "name": "IIP, ISIC Revision 4",
            "countries": [],
            "periods": ["2025"],
            "variables": [{"c": "53"}],
        }
        with self.assertRaisesRegex(ValueError, "original index"):
            parse_metadata(metadata)

    def test_export_filters_original_total_manufacturing(self):
        raw = pd.DataFrame([
            {"Year": 2020, "Country": "A", "CountryCode": 1, "VariableCode": 52,
             "ActivityCode": "C", "Value": 100.0},
            {"Year": 2020, "Country": "A", "CountryCode": 1, "VariableCode": 53,
             "ActivityCode": "C", "Value": 99.0},
            {"Year": 2020, "Country": "A", "CountryCode": 1, "VariableCode": 52,
             "ActivityCode": "10", "Value": 101.0},
        ])
        parsed = parse_iip_export(raw)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(float(parsed.iloc[0]["iip"]), 100.0)

    def test_balanced_panel_uses_fixed_weights_and_reports_coverage(self):
        iip = pd.DataFrame([
            {"year": 2020, "country": "A", "country_code": 1, "iip": 100.0},
            {"year": 2021, "country": "A", "country_code": 1, "iip": 110.0},
            {"year": 2020, "country": "B", "country_code": 2, "iip": 100.0},
            {"year": 2021, "country": "B", "country_code": 2, "iip": 90.0},
            {"year": 2020, "country": "C", "country_code": 3, "iip": 100.0},
        ])
        weights = pd.DataFrame([
            {"country": "A", "country_code": 1, "mva_current_2020_usd": 3.0},
            {"country": "B", "country_code": 2, "mva_current_2020_usd": 1.0},
            {"country": "C", "country_code": 3, "mva_current_2020_usd": 1.0},
        ])
        result, diagnostics = aggregate_balanced_panel(
            iip, weights, start_year=2020, end_year=2021
        )
        self.assertAlmostEqual(float(result.loc[result.year.eq(2021), "manufacturing_iip_2020_100"].iloc[0]), 105.0)
        self.assertEqual(diagnostics["balanced_country_count"], 2)
        self.assertAlmostEqual(diagnostics["mva_2020_weight_coverage_pct"], 80.0)

    def test_weight_parser_uses_current_2020_mva_only(self):
        raw = pd.DataFrame([
            {"Year": 2020, "Country": "A", "CountryCode": 1, "VariableCode": "MvaCud", "Value": 3.0},
            {"Year": 2020, "Country": "A", "CountryCode": 1, "VariableCode": "MvaCod", "Value": 4.0},
        ])
        parsed = parse_mva_weights(raw)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(float(parsed.iloc[0]["mva_current_2020_usd"]), 3.0)


if __name__ == "__main__":
    unittest.main()
