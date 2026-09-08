import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "unido_national_accounts_world_2026-09-07.csv"
OUTPUT = ROOT / "outputs" / "unido_industry_proxy"


class UnidoIndustryProxyTests(unittest.TestCase):
    def test_snapshot_is_complete_positive_and_normalized(self):
        frame = pd.read_csv(DATA).set_index("year")
        self.assertEqual(frame.index.min(), 1990)
        self.assertEqual(frame.index.max(), 2025)
        self.assertEqual(len(frame), 36)
        self.assertFalse(frame.isna().any().any())
        self.assertTrue((frame.drop(columns="mva_per_capita_index_2015") > 0).all().all())
        self.assertAlmostEqual(float(frame.loc[2015, "mva_per_capita_index_2015"]), 100.0)

    def test_audit_keeps_production_projection_frozen(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["central_projection_changed"])
        self.assertEqual(manifest["observation_count"], 36)
        self.assertTrue(manifest["latest_year_is_unido_estimate"])
        self.assertTrue(manifest["status"].startswith("accepted_as_independent"))
        self.assertEqual(
            manifest["data_decision"],
            "add_to_observed_data_registry_as_independent_benchmark",
        )
        self.assertIn("v0.10.0", manifest["calibration_decision"])
        self.assertGreater(manifest["annual_log_growth_correlation"], 0.9)

    def test_cross_proxy_backtest_is_complete(self):
        frame = pd.read_csv(OUTPUT / "cross_proxy_backtest.csv")
        self.assertEqual(len(frame), 12)
        self.assertEqual(set(frame["origin"]), {2009, 2014, 2018})
        self.assertEqual(
            set(frame["selector_proxy"]), {"world_bank_industry", "unido_mva"}
        )
        self.assertEqual(
            set(frame["evaluation_proxy"]), {"world_bank_industry", "unido_mva"}
        )
        self.assertTrue((frame[["log_rmse", "mape_pct"]] >= 0).all().all())

    def test_projection_comparison_covers_five_targets_and_two_horizons(self):
        frame = pd.read_csv(OUTPUT / "production_projection_comparison.csv")
        self.assertEqual(len(frame), 10)
        self.assertEqual(set(frame["year"]), {2030, 2035})
        self.assertEqual(frame["indicator"].nunique(), 5)
        self.assertFalse(frame.isna().any().any())

    def test_observed_proxy_comparison_covers_full_overlap(self):
        frame = pd.read_csv(OUTPUT / "observed_proxy_comparison.csv")
        self.assertEqual(frame["year"].min(), 1992)
        self.assertEqual(frame["year"].max(), 2025)
        self.assertEqual(len(frame), 34)
        self.assertAlmostEqual(
            float(frame.loc[frame["year"].eq(2015), "index_difference_pct"].iloc[0]),
            0.0,
            places=10,
        )


if __name__ == "__main__":
    unittest.main()
