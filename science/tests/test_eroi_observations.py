import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "energy_coupling"


class EROIObservationTests(unittest.TestCase):
    def test_boundaries_are_stored_separately(self):
        frame = pd.read_csv(
            ROOT / "data" / "processed" / "aramendia_global_fossil_eroi_2024.csv"
        )
        self.assertEqual((int(frame.year.min()), int(frame.year.max())), (1971, 2020))
        latest = frame.iloc[-1]
        self.assertGreater(latest.fossil_primary_eroi_including_indirect, 20)
        self.assertLess(latest.fossil_final_eroi_including_indirect, 10)
        self.assertLess(latest.fossil_useful_eroi_including_indirect, 4)

    def test_resource_link_fails_declared_acceptance_rule(self):
        manifest = json.loads((OUTPUT / "eroi_resource_link_manifest.json").read_text())
        self.assertFalse(manifest["accepted"])
        summary = pd.read_csv(OUTPUT / "eroi_resource_link_summary.csv")
        pivot = summary.pivot(index="boundary", columns="model", values="rmse")
        self.assertTrue(
            (pivot.world3_resource_link > pivot.persistence).all()
        )


if __name__ == "__main__":
    unittest.main()
