import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "climate_food"


class ClimateFoodTests(unittest.TestCase):
    def test_gistemp_snapshot_is_complete_and_versioned(self):
        frame = pd.read_csv(
            ROOT / "data" / "processed" / "nasa_gistemp_global_2026.csv"
        )
        self.assertEqual((int(frame.year.min()), int(frame.year.max())), (1880, 2025))
        self.assertFalse(frame.year.duplicated().any())
        provenance = json.loads(
            (
                ROOT
                / "data"
                / "processed"
                / "nasa_gistemp_global_2026.provenance.json"
            ).read_text()
        )
        self.assertEqual(
            provenance["raw_sha256"],
            "6cfa44e7bbacd9b12cb10bdd64b3182c2735fa3f3a95688e1f7bc8e5dfcece93",
        )

    def test_backtest_has_no_future_information(self):
        frame = pd.read_csv(OUTPUT / "climate_food_backtest.csv")
        self.assertTrue((frame["food_training_end"] <= frame["origin"]).all())
        self.assertTrue((frame["temperature_training_end"] <= frame["origin"]).all())
        self.assertTrue((frame["test_start"] > frame["origin"]).all())

    def test_simple_climate_bridge_fails_independent_holdout(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text())
        self.assertFalse(manifest["accepted"])
        summary = pd.read_csv(OUTPUT / "climate_food_summary.csv").set_index("period")
        holdout = summary.loc["independent_2019_2024"]
        self.assertGreater(
            holdout.climate_bridge_log_rmse,
            holdout.existing_bridge_log_rmse,
        )


if __name__ == "__main__":
    unittest.main()
