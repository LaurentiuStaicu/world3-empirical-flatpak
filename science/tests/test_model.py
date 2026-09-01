import unittest

import numpy as np

from world3_empirical import run_scenario


class ModelTests(unittest.TestCase):
    def test_standard_run_is_finite_and_has_expected_initial_population(self):
        result = run_scenario("world3_standard", year_max=1910)
        self.assertTrue(np.isfinite(result.frame.to_numpy()).all())
        self.assertAlmostEqual(result.frame.iloc[0]["population"], 1.6e9)

    def test_resource_rich_proxy_starts_with_twice_the_resource_stock(self):
        standard = run_scenario("world3_standard", year_max=1901)
        proxy = run_scenario("bau2_structural_proxy", year_max=1901)
        ratio = proxy.frame.iloc[0]["nonrenewable_resources"] / standard.frame.iloc[0]["nonrenewable_resources"]
        self.assertAlmostEqual(ratio, 2.0)
        self.assertEqual(proxy.scenario.evidence_status, "proxy_not_reference_exact")


if __name__ == "__main__":
    unittest.main()

