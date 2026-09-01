import unittest

import numpy as np

from world3_empirical.net_energy import NetEnergyParameters, run_named_scenarios, simulate_net_energy


class NetEnergyTests(unittest.TestCase):
    def setUp(self):
        self.frame = simulate_net_energy(NetEnergyParameters(end_year=2050))

    def test_energy_identity(self):
        expected = self.frame["gross_energy_index"] * (
            1.0 - 1.0 / self.frame["system_eroi"]
        )
        np.testing.assert_allclose(self.frame["net_energy_index_raw"], expected)

    def test_reinvestment_identity(self):
        np.testing.assert_allclose(
            self.frame["energy_reinvestment_pct"],
            100.0 / self.frame["system_eroi"],
        )

    def test_resource_stock_never_increases(self):
        self.assertTrue((self.frame["fossil_resource_fraction"].diff().dropna() <= 0).all())

    def test_declared_initial_conditions_are_exact(self):
        first = self.frame.iloc[0]
        self.assertAlmostEqual(first["gross_energy_index"], 100.0)
        self.assertAlmostEqual(first["fossil_share"], 0.8623843748)
        self.assertAlmostEqual(first["fossil_resource_fraction"], 0.65)

    def test_net_energy_is_below_gross_energy(self):
        self.assertTrue(
            (self.frame["net_energy_index_raw"] < self.frame["gross_energy_index"]).all()
        )

    def test_named_scenarios_are_complete(self):
        result = run_named_scenarios()
        self.assertEqual(
            set(result["scenario"]),
            {"quality_decline", "accelerated_transition", "fossil_lock_in_stress"},
        )
        self.assertFalse(result.isna().any().any())

    def test_invalid_eroi_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_net_energy(NetEnergyParameters(fossil_eroi_floor=1.0))


if __name__ == "__main__":
    unittest.main()
