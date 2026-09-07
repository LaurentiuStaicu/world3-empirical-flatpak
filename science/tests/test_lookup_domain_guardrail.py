import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "lookup_domain_guardrail"


class LookupDomainGuardrailTests(unittest.TestCase):
    def test_audit_does_not_change_the_central_model(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "rejected")
        self.assertEqual(
            manifest["production_decision"],
            "do_not_change_BAU_Hybrid_2026_v0.10.0",
        )
        self.assertIn("events_q25", manifest["chosen_on_development_only"])

    def test_temporal_lookup_cutoff_never_exceeds_forecast_origin(self):
        backtest = pd.read_csv(OUTPUT / "policy_backtest.csv")
        self.assertTrue(
            backtest["lookup_information_cutoff"].eq(backtest["origin"]).all()
        )
        self.assertEqual(sorted(backtest["origin"].unique()), [2005, 2010, 2015, 2018])

    def test_metrics_cover_every_candidate_at_every_origin(self):
        metrics = pd.read_csv(OUTPUT / "candidate_lookup_metrics.csv")
        self.assertEqual(len(metrics), 128 * 4)
        self.assertEqual(metrics["candidate_id"].nunique(), 128)
        self.assertTrue((metrics[["events", "material_events", "lookups"]] >= 0).all().all())
        self.assertTrue((metrics["distance_exposure"] >= 0.0).all())

    def test_best_development_policy_fails_the_promotion_rule(self):
        summary = pd.read_csv(OUTPUT / "policy_summary.csv")
        chosen = summary.sort_values(
            ["development_log_rmse", "independent_log_rmse", "policy"]
        ).iloc[0]
        self.assertEqual(chosen["policy"], "events_q25")
        self.assertLess(chosen["development_improvement_pct"], 5.0)
        self.assertLess(chosen["independent_improvement_pct"], 5.0)
        self.assertGreater(
            chosen["maximum_independent_sector_worsening_pct"], 100.0
        )
        self.assertFalse(bool(chosen["accepted"]))

    def test_independent_sector_failures_remain_visible(self):
        comparison = pd.read_csv(OUTPUT / "chosen_policy_comparison.csv")
        recent = comparison.loc[comparison["origin"].eq(2018)].set_index("indicator")
        self.assertLess(recent.loc["population", "improvement_pct"], -100.0)
        self.assertLess(recent.loc["food_per_capita", "improvement_pct"], -10.0)


if __name__ == "__main__":
    unittest.main()
