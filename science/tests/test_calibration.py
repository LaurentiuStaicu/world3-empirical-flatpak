import unittest

import pandas as pd

from world3_empirical.calibration import calibrate, monte_carlo
from world3_empirical.model import run_scenario


class CalibrationTests(unittest.TestCase):
    def test_calibration_recovers_synthetic_resource_stock(self):
        truth = run_scenario("world3_standard", year_min=1900, year_max=1930, extra_constants={"nri": 1.2e12}).frame
        sampled = truth.loc[truth["year"].isin([1900, 1905, 1910, 1915, 1920, 1925, 1930]), ["year", "nonrenewable_resources"]]
        observations = sampled.rename(columns={"nonrenewable_resources": "value"}).copy()
        observations["variable"] = "nonrenewable_resources"
        observations["split"] = ["train"] * 5 + ["test"] * 2
        fitted = calibrate(observations, {"nri": (0.8e12, 1.5e12)}, max_nfev=50)
        self.assertTrue(fitted.success)
        self.assertAlmostEqual(fitted.parameters["nri"] / 1.2e12, 1.0, places=3)
        self.assertFalse(fitted.test_metrics.empty)

    def test_monte_carlo_returns_requested_quantiles(self):
        table = monte_carlo({"nri": (0.9e12, 1.1e12)}, samples=4, years=(2025,), variables=("population",))
        self.assertEqual(list(table.columns), ["year", "variable", "p05", "median", "p95"])
        self.assertEqual(len(table), 1)


if __name__ == "__main__":
    unittest.main()

