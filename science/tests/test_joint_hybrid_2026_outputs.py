import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "joint_hybrid_2026"
INDICATORS = (
    "population",
    "industry_per_capita",
    "food_per_capita",
    "pollution_pressure",
    "human_welfare",
)
DIAGNOSTICS = (
    "industry_total",
    "persistent_pollution_stock",
    "resources_remaining_pct",
)


class JointHybrid2026OutputTests(unittest.TestCase):
    def rows(self, indicator):
        with (OUTPUT / f"{indicator}.csv").open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_manifest_declares_one_joint_world3_run(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["model"], "BAU Hybrid 2026 Joint")
        self.assertEqual(manifest["structural_model"], "official World3-03 scenario 2 (BAU2)")
        self.assertEqual(manifest["version"], "0.10.0")
        self.assertEqual(manifest["candidate_count"], 128)
        self.assertEqual(manifest["selection_cutoff"], 2018)
        self.assertEqual(manifest["production_fit_cutoff"], 2025)
        self.assertNotEqual(
            manifest["validation_candidate_id"], manifest["production_candidate_id"]
        )
        self.assertEqual(manifest["central_mapping_boundary_count_at_selection"], 0)
        self.assertEqual(manifest["central_plausibility_violation_count"], 0)
        self.assertEqual(len(manifest["central_parameters"]), 7)
        self.assertGreaterEqual(len(manifest["ensemble_candidate_ids"]), 12)
        self.assertIn(manifest["central_candidate_id"], manifest["ensemble_candidate_ids"])
        self.assertIn("not a probabilistic forecast", manifest["scientific_status"])

    def test_each_series_is_exactly_anchored_at_latest_observation(self):
        for indicator in INDICATORS:
            rows = self.rows(indicator)
            observed = [row for row in rows if row["observed"]]
            latest = observed[-1]
            self.assertAlmostEqual(
                float(latest["observed"]),
                float(latest["hybrid_2026"]),
                places=6,
                msg=indicator,
            )

    def test_sensitivity_quantiles_are_ordered_without_forcing_the_medoid(self):
        for indicator in INDICATORS + DIAGNOSTICS:
            for row in self.rows(indicator):
                if not row["sensitivity_low"]:
                    continue
                self.assertLessEqual(
                    float(row["sensitivity_low"]),
                    float(row["sensitivity_high"]),
                    indicator,
                )
        resources_2030 = next(
            row for row in self.rows("resources_remaining_pct") if row["year"] == "2030"
        )
        self.assertLess(
            float(resources_2030["hybrid_2026"]),
            float(resources_2030["sensitivity_low"]),
            "The latent-resource medoid must not be artificially inserted into P10-P90",
        )

    def test_recent_holdout_improves_most_indicators_and_weighted_error(self):
        with (OUTPUT / "backtest_2019_latest.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), len(INDICATORS))
        improved = sum(float(row["improvement_pct"]) > 0 for row in rows)
        self.assertEqual(improved, 5)
        weights = [int(row["n"]) for row in rows]
        reference = sum(
            weight * float(row["bau2_level_anchored_mape_pct"])
            for weight, row in zip(weights, rows)
        ) / sum(weights)
        hybrid = sum(
            weight * float(row["bau2_e2026_mape_pct"])
            for weight, row in zip(weights, rows)
        ) / sum(weights)
        self.assertLess(hybrid, reference)

    def test_observation_bridges_are_pre2019_and_do_not_replace_world3(self):
        manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
        bridges = manifest["observation_bridges"]
        self.assertEqual(bridges["selection_cutoff"], 2018)
        self.assertAlmostEqual(
            bridges["food_per_capita"]["world3_food_weight"], 0.25
        )
        self.assertAlmostEqual(
            bridges["pollution_pressure"][
                "world3_persistent_pollution_generation_weight"
            ],
            0.0,
        )
        self.assertIn("do not alter structural selection", manifest["method"])

    def test_bridge_weight_search_is_exported_and_has_one_choice_per_sector(self):
        with (OUTPUT / "bridge_validation.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 10)
        chosen = {row["sector"]: row for row in rows if row["chosen"] == "True"}
        self.assertEqual(set(chosen), {"food_per_capita", "pollution_pressure"})
        self.assertAlmostEqual(float(chosen["food_per_capita"]["world3_signal_weight"]), 0.25)
        self.assertAlmostEqual(float(chosen["pollution_pressure"]["world3_signal_weight"]), 0.0)

    def test_food_and_pollution_bridges_improve_multi_origin_validation(self):
        with (OUTPUT / "backtest_multi_origin.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = {row["key"]: row for row in csv.DictReader(handle)}
        for indicator in ("food_per_capita", "pollution_pressure"):
            self.assertGreater(float(rows[indicator]["improvement_pct"]), 0.0)

    def test_population_recent_holdout_is_improved(self):
        with (OUTPUT / "backtest_2019_latest.csv").open(newline="", encoding="utf-8") as handle:
            rows = {row["key"]: row for row in csv.DictReader(handle)}
        population = rows["population"]
        ratio = (
            float(population["bau2_e2026_mape_pct"])
            / float(population["bau2_level_anchored_mape_pct"])
        )
        self.assertLess(ratio, 1.0)

    def test_latent_diagnostics_do_not_claim_observations(self):
        industry = self.rows("industry_total")
        self.assertTrue(any(row["observed"] for row in industry))
        for indicator in DIAGNOSTICS[1:]:
            self.assertFalse(any(row["observed"] for row in self.rows(indicator)))

    def test_total_industry_is_anchored_at_latest_observation(self):
        observed = [row for row in self.rows("industry_total") if row["observed"]]
        latest = observed[-1]
        self.assertAlmostEqual(
            float(latest["observed"]), float(latest["hybrid_2026"]), places=6
        )

    def test_resources_use_one_common_bau_1900_denominator(self):
        rows = {int(row["year"]): row for row in self.rows("resources_remaining_pct")}
        # Export starts in 1950, so values must already show that BAU2 and the
        # hybrid began with more than the BAU-1900 stock of 100.
        self.assertLess(float(rows[1950]["original_bau"]), 100.0)
        self.assertGreater(float(rows[1950]["original_bau2"]), 100.0)
        self.assertGreater(float(rows[1950]["hybrid_2026"]), 100.0)

    def test_production_ensemble_obeys_declared_guardrails(self):
        ranking = {}
        with (OUTPUT / "candidate_ranking.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                ranking[int(row["candidate_id"])] = row
        manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
        for candidate_id in manifest["ensemble_candidate_ids"]:
            self.assertEqual(int(ranking[candidate_id]["mapping_boundary_count"]), 0)
            self.assertEqual(int(ranking[candidate_id]["plausibility_violation_count"]), 0)

    def test_identifiability_report_covers_all_parameters(self):
        with (OUTPUT / "parameter_identifiability.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 7)
        weak = sum(row["weakly_identified"] == "True" for row in rows)
        self.assertGreaterEqual(weak, 5)

    def test_lookup_extrapolation_detail_reconciles_to_candidate_totals(self):
        with (OUTPUT / "lookup_extrapolation_audit.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            audit = {int(row["candidate_id"]): row for row in csv.DictReader(handle)}
        with (OUTPUT / "lookup_extrapolation_detail.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            details = list(csv.DictReader(handle))

        counts = {candidate_id: 0 for candidate_id in audit}
        unique = {candidate_id: 0 for candidate_id in audit}
        for row in details:
            candidate_id = int(row["candidate_id"])
            self.assertIn(row["direction"], {"above", "below"})
            self.assertTrue(row["lookup"].startswith("_hardcodedlookup_"))
            counts[candidate_id] += int(row["count"])
            unique[candidate_id] += 1

        self.assertEqual(len(audit), 128)
        for candidate_id, row in audit.items():
            self.assertEqual(counts[candidate_id], int(row["total"]))
            self.assertEqual(unique[candidate_id], int(row["unique"]))

        central_rows = [row for row in details if int(row["candidate_id"]) == 114]
        central_lookups = {row["lookup"] for row in central_rows}
        self.assertIn("_hardcodedlookup_capacity_utilization_fraction_table", central_lookups)
        self.assertIn("_hardcodedlookup_land_fertility_degredation_rate_table", central_lookups)


if __name__ == "__main__":
    unittest.main()
