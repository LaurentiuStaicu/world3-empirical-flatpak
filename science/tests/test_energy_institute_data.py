import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class EnergyInstituteDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = pd.read_csv(
            ROOT / "data" / "processed" / "energy_institute_global_2026.csv"
        )

    def test_expected_coverage_and_unique_years(self):
        self.assertEqual(int(self.frame.year.min()), 1965)
        self.assertEqual(int(self.frame.year.max()), 2025)
        self.assertEqual(len(self.frame), 61)
        self.assertFalse(self.frame.year.duplicated().any())

    def test_energy_components_reconcile(self):
        components = self.frame[
            ["oil_ej", "gas_ej", "coal_ej", "nuclear_ej", "hydro_ej", "renewables_ej"]
        ].sum(axis=1)
        relative_error = (
            (components - self.frame.total_primary_energy_ej).abs()
            / self.frame.total_primary_energy_ej
        ).max()
        self.assertLess(relative_error, 0.001)
        stored = self.frame.component_reconciliation_error_ej
        calculated = components - self.frame.total_primary_energy_ej
        self.assertLess((stored - calculated).abs().max(), 1e-7)

    def test_2025_fossil_share_is_observed_anchor(self):
        latest = self.frame.loc[self.frame.year == 2025].iloc[0]
        self.assertAlmostEqual(latest.fossil_share, 0.862383, places=5)
        self.assertGreater(latest.total_primary_energy_ej, 600)


if __name__ == "__main__":
    unittest.main()
