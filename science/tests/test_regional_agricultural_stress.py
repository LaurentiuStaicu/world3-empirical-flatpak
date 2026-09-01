import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "regional_agricultural_stress"


class RegionalAgriculturalStressTests(unittest.TestCase):
    def test_panel_is_unique_and_has_high_post_transition_coverage(self):
        panel = pd.read_csv(
            ROOT / "data" / "processed" / "regional_cereal_climate_panel_2026.csv"
        )
        self.assertEqual((int(panel.year.min()), int(panel.year.max())), (1961, 2024))
        self.assertFalse(panel.duplicated(["code", "year"]).any())
        self.assertGreaterEqual(panel.code.nunique(), 170)
        provenance = json.loads(
            (
                ROOT
                / "data"
                / "processed"
                / "regional_cereal_climate_panel_2026.provenance.json"
            ).read_text()
        )
        self.assertGreaterEqual(
            provenance["world_production_coverage"]["minimum_1992_latest"], 0.98
        )
        self.assertEqual(
            provenance["raw_files"][
                "data/raw/faostat/Production_Crops_Livestock_E_All_Data_Normalized_2025.zip"
            ],
            "c5835418c18f9322e7decbd6800f93a216eaae3cdfa31acb08f0518c0c6d6853",
        )

    def test_prospective_backtest_has_no_future_information(self):
        frame = pd.read_csv(OUTPUT / "regional_stress_backtest.csv")
        for column in (
            "food_training_end",
            "climate_training_end",
            "weight_training_end",
        ):
            self.assertTrue((frame[column] <= frame["origin"]).all())
        self.assertTrue((frame["test_start"] > frame["origin"]).all())
        self.assertGreaterEqual(frame["eligible_production_share"].min(), 0.90)

    def test_regional_bridge_is_rejected_by_predeclared_rule(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text())
        self.assertFalse(manifest["accepted"])
        summary = pd.read_csv(OUTPUT / "regional_stress_summary.csv").set_index(
            "period"
        )
        development = summary.loc["development_pre2019"]
        self.assertGreater(
            development.prospective_climate_log_rmse,
            development.existing_bridge_log_rmse,
        )


if __name__ == "__main__":
    unittest.main()
