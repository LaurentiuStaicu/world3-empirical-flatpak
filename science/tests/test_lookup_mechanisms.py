import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
JOINT_OUTPUT = ROOT / "outputs" / "joint_hybrid_2026"
OUTPUT = ROOT / "outputs" / "lookup_mechanisms"
MECHANISMS = {
    "affluence_material_demand",
    "agriculture_land_food",
    "fertility_social_response",
    "health_mortality",
    "labor_capacity",
    "pollution_ecology",
}


class LookupMechanismAuditTests(unittest.TestCase):
    def test_taxonomy_covers_every_causal_lookup_exactly_once(self):
        context = pd.read_csv(JOINT_OUTPUT / "lookup_extrapolation_context.csv")
        expected = set(
            context.loc[
                ~context["lookup"].str.contains("scenario_table", case=False, na=False),
                "lookup",
            ]
        )
        mapping = pd.read_csv(OUTPUT / "lookup_mechanism_mapping.csv")
        self.assertEqual(len(mapping), 33)
        self.assertEqual(mapping["lookup"].nunique(), 33)
        self.assertEqual(set(mapping["lookup"]), expected)
        self.assertEqual(set(mapping["mechanism"]), MECHANISMS)

    def test_metrics_are_complete_and_temporally_honest(self):
        metrics = pd.read_csv(OUTPUT / "candidate_mechanism_metrics.csv")
        self.assertEqual(len(metrics), 128 * 4 * len(MECHANISMS))
        self.assertEqual(metrics["candidate_id"].nunique(), 128)
        self.assertEqual(set(metrics["mechanism"]), MECHANISMS)
        self.assertEqual(sorted(metrics["origin"].unique()), [2005, 2010, 2015, 2018])
        self.assertTrue(
            metrics["lookup_information_cutoff"].eq(metrics["origin"]).all()
        )
        self.assertTrue(
            (metrics[["events", "material_events", "lookups"]] >= 0).all().all()
        )
        self.assertTrue((metrics["distance_exposure"] >= 0.0).all())

    def test_development_score_alone_selects_the_reported_policy(self):
        summary = pd.read_csv(OUTPUT / "policy_summary.csv")
        chosen = summary.loc[summary["feasible"]].sort_values(
            ["development_log_rmse", "policy"]
        ).iloc[0]
        manifest = json.loads((OUTPUT / "manifest.json").read_text())
        self.assertEqual(chosen["policy"], manifest["chosen_on_development_only"])
        self.assertEqual(chosen["mechanism"], manifest["chosen_mechanism"])
        self.assertEqual(bool(chosen["accepted"]), manifest["status"] == "accepted")
        self.assertEqual(
            manifest["chosen_on_development_only"],
            "fertility_social_response__distance_exposure_q25",
        )
        self.assertAlmostEqual(
            manifest["chosen_development_improvement_pct"], 2.0858834319, places=8
        )
        self.assertAlmostEqual(
            manifest["chosen_temporal_comparison_improvement_pct"],
            -11.6379945796,
            places=8,
        )
        self.assertGreater(
            manifest["chosen_maximum_temporal_sector_worsening_pct"], 276.0
        )
        self.assertEqual(manifest["status"], "rejected")
        self.assertEqual(
            manifest["production_decision"],
            "do_not_change_BAU_Hybrid_2026_v0.10.0",
        )

    def test_reused_temporal_comparison_is_disclosed(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text())
        self.assertTrue(manifest["taxonomy_frozen_before_policy_evaluation"])
        self.assertTrue(manifest["temporal_comparison_reused_across_project_audits"])
        self.assertEqual(manifest["temporal_comparison_origin"], 2018)
        self.assertIn("not a globally untouched", manifest["interpretation_limit"])

    def test_central_inventory_keeps_all_mechanisms_visible(self):
        inventory = pd.read_csv(OUTPUT / "central_mechanism_inventory.csv")
        self.assertEqual(set(inventory["mechanism"]), MECHANISMS)
        self.assertEqual(len(inventory), len(MECHANISMS))
        self.assertTrue(
            (inventory[["events", "material_events", "post_2025_events"]] >= 0)
            .all()
            .all()
        )


if __name__ == "__main__":
    unittest.main()
