import json
import gzip
import hashlib
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "minerals" / "2026-09-08"
PRODUCTION = ROOT / "data" / "processed" / "technology_mineral_production_2026-09-08.csv"
RISK = ROOT / "data" / "processed" / "technology_mineral_risk_2026-09-08.csv"
OUTPUT = ROOT / "outputs" / "technology_minerals"


class TechnologyMineralAuditTests(unittest.TestCase):
    def test_normalized_usgs_snapshot_restores_official_hash(self):
        normalized = gzip.decompress(
            (RAW / "MCS2026_Commodities_Data.normalized-lf.csv.gz").read_bytes()
        )
        self.assertNotIn(b"\r\n", normalized)
        official_bytes = normalized.replace(b"\n", b"\r\n")
        self.assertEqual(
            hashlib.md5(official_bytes).hexdigest(),
            "36185ff3742087e1dd90c52fe634fe12",
        )
        self.assertEqual(
            hashlib.sha256(official_bytes).hexdigest(),
            "582a0aa231aea53d8a97dc8d1cd3dfa5f885cf3760353e3d029d7f0ae4fbaaf5",
        )

    def test_production_snapshot_is_positive_and_has_latest_endpoint(self):
        frame = pd.read_csv(PRODUCTION)
        self.assertEqual(set(frame["commodity"]), {
            "cobalt", "copper", "graphite", "lithium", "nickel", "rare_earths",
        })
        self.assertTrue((frame["production_tonnes"] > 0).all())
        self.assertTrue((frame.groupby("commodity")["year"].max() == 2025).all())
        base = frame.loc[frame["year"].eq(2015), "production_index_2015_100"]
        self.assertTrue((base.round(12) == 100.0).all())

    def test_risk_table_preserves_hhi_uncertainty_and_revision_conflict(self):
        frame = pd.read_csv(RISK).set_index("commodity")
        self.assertEqual(len(frame), 6)
        self.assertTrue((frame["production_hhi_lower_bound"] <= frame["production_hhi_upper_bound"]).all())
        self.assertTrue(frame["production_2025_estimated"].all())
        self.assertEqual(
            frame.loc["rare_earths", "reserve_status"],
            "excluded_data_release_vs_report_v1_3_conflict",
        )
        self.assertTrue(pd.isna(frame.loc["rare_earths", "reserve_to_annual_output_ratio"]))

    def test_audit_is_registry_only_and_central_projection_is_unchanged(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["status"],
            "accepted_as_observed_risk_registry_not_central_calibration",
        )
        self.assertFalse(manifest["central_projection_changed"])
        self.assertEqual(manifest["latest_observation_year"], 2025)
        self.assertGreaterEqual(len(manifest["central_rejection_reasons"]), 5)


if __name__ == "__main__":
    unittest.main()
