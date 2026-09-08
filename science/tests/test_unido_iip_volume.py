import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "unido_iip_world_public_2026-09-08.csv"
PROVENANCE = DATA.with_suffix(".provenance.json")
OUTPUT = ROOT / "outputs" / "unido_iip_volume"


class UnidoIipVolumeTests(unittest.TestCase):
    def test_snapshot_is_complete_positive_and_normalized(self):
        frame = pd.read_csv(DATA).set_index("year")
        self.assertEqual(frame.index.min(), 2005)
        self.assertEqual(frame.index.max(), 2025)
        self.assertEqual(len(frame), 21)
        self.assertFalse(frame.isna().any().any())
        self.assertTrue((frame > 0).all().all())
        self.assertAlmostEqual(
            float(frame.loc[2015, "manufacturing_iip_per_capita_index_2015"]), 100.0
        )

    def test_public_panel_has_declared_coverage(self):
        provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertEqual(provenance["weight_base_year"], 2020)
        self.assertEqual(provenance["balanced_country_count"], 101)
        self.assertGreater(provenance["mva_2020_weight_coverage_pct"], 90.0)
        self.assertIn("not UNIDO's official world aggregate", provenance["interpretation_limit"])

    def test_audit_is_diagnostic_and_does_not_silently_fill_2009(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["central_projection_changed"])
        self.assertTrue(manifest["public_reconstruction_not_official_world_aggregate"])
        self.assertEqual(manifest["origins"], [2014, 2018])
        self.assertEqual(manifest["unavailable_standard_origin"], 2009)
        self.assertEqual(manifest["observation_count"], 21)
        self.assertTrue(manifest["status"].startswith("accepted_as_"))

    def test_cross_proxy_backtest_is_complete(self):
        frame = pd.read_csv(OUTPUT / "cross_proxy_backtest.csv")
        self.assertEqual(len(frame), 8)
        self.assertEqual(set(frame["origin"]), {2014, 2018})
        self.assertEqual(set(frame["selector_proxy"]), {"world_bank_industry", "unido_iip_volume"})
        self.assertEqual(set(frame["evaluation_proxy"]), {"world_bank_industry", "unido_iip_volume"})
        self.assertTrue((frame[["log_rmse", "mape_pct"]] >= 0).all().all())

    def test_projection_comparison_is_complete(self):
        frame = pd.read_csv(OUTPUT / "production_projection_comparison.csv")
        self.assertEqual(len(frame), 10)
        self.assertEqual(set(frame["year"]), {2030, 2035})
        self.assertEqual(frame["indicator"].nunique(), 5)
        self.assertFalse(frame.isna().any().any())


if __name__ == "__main__":
    unittest.main()
