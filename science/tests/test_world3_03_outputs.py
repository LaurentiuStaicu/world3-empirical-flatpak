import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class World303ReferenceOutputTests(unittest.TestCase):
    def test_bau2_reference_checkpoints(self):
        frame = pd.read_csv(ROOT / "outputs" / "world3_03_bau2.csv").set_index("year")
        self.assertAlmostEqual(frame.loc[1900.0, "nonrenewable_resources"], 2e12, delta=1e3)
        self.assertAlmostEqual(frame.loc[2030.0, "population"], 7.897073e9, delta=2e5)
        self.assertAlmostEqual(frame.loc[2030.0, "persistent_pollution_index"], 10.800535, places=5)

    def test_bau_and_bau2_are_identical_at_initial_year_except_resources(self):
        bau = pd.read_csv(ROOT / "outputs" / "world3_03_bau.csv").set_index("year")
        bau2 = pd.read_csv(ROOT / "outputs" / "world3_03_bau2.csv").set_index("year")
        for variable in ("population", "industrial_output_per_capita", "food_per_capita"):
            self.assertAlmostEqual(bau.loc[1900.0, variable], bau2.loc[1900.0, variable])
        self.assertEqual(bau2.loc[1900.0, "nonrenewable_resources"], 2 * bau.loc[1900.0, "nonrenewable_resources"])


if __name__ == "__main__":
    unittest.main()

