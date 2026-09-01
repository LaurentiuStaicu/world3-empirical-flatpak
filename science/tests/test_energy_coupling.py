import json
import unittest
from pathlib import Path

import pandas as pd

from world3_empirical.energy_coupling import (
    EROICouplingParameters,
    coupled_model_text,
)
from world3_empirical.world3_03 import _sanitized_model_text, _source_model_path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "energy_coupling"


class EnergyCouplingTests(unittest.TestCase):
    def test_injection_replaces_instead_of_adding_resource_burdens(self):
        result = coupled_model_text(_sanitized_model_text(_source_model_path()))
        self.assertIn("MAX ( world3 fraction", result)
        self.assertNotIn(
            "world3 fraction of industrial capital allocated to obtaining resources +",
            result,
        )
        self.assertEqual(result.lower().count("energy system eroi ="), 1)

    def test_invalid_eroi_prior_is_rejected(self):
        with self.assertRaises(ValueError):
            EROICouplingParameters(fossil_eroi_floor=1.0).model_parameters()

    def test_audit_preserves_the_production_boundary(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text())
        self.assertEqual(
            manifest["production_decision"], "not_accepted_into_central_projection"
        )
        self.assertEqual(
            manifest["pre2025_coupled_vs_uncoupled_max_absolute_difference"], 0.0
        )
        self.assertEqual(
            manifest["uncoupled_patch_invariance_max_absolute_difference"], 0.0
        )
        self.assertAlmostEqual(manifest["observed_fossil_share_2025"], 0.8623843748)
        self.assertEqual(
            manifest["eroi_accounting_boundary"],
            "final-stage EROI, indirect energy included",
        )
        self.assertEqual(manifest["fossil_eroi_anchor_year"], 2020)
        self.assertAlmostEqual(manifest["fossil_eroi_anchor_value"], 8.4694506689)
        self.assertFalse(manifest["resource_link_accepted"])
        self.assertEqual(
            manifest["scenarios"]["conservative_central"][
                "resource_fraction_reference"
            ],
            manifest["resource_fraction_reference_2025"],
        )

    def test_near_term_scenario_order_is_interpretable(self):
        frame = pd.read_csv(OUTPUT / "scenario_summary.csv")
        for year in (2030, 2035, 2050):
            values = frame.loc[frame["year"].eq(year)].set_index("scenario")
            self.assertGreaterEqual(
                values.loc["accelerated_transition", "industry_per_capita"],
                values.loc["conservative_central", "industry_per_capita"],
            )
            self.assertGreaterEqual(
                values.loc["conservative_central", "industry_per_capita"],
                values.loc["fossil_lock_in_stress", "industry_per_capita"],
            )

    def test_coupling_is_continuous_in_2025(self):
        frame = pd.read_csv(OUTPUT / "scenario_summary.csv")
        boundary = frame.loc[frame["year"].eq(2025)]
        self.assertTrue((boundary["energy_capital_burden_pct"] == 5.0).all())
        self.assertTrue(
            (boundary["effective_resource_capital_burden_pct"] == 5.0).all()
        )


if __name__ == "__main__":
    unittest.main()
