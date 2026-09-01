from pathlib import Path
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "bau2_e2026"


class Bau2E2026OutputTests(unittest.TestCase):
    def test_forecasts_start_at_latest_observation(self):
        for key in (
            "population",
            "industry_per_capita",
            "food_per_capita",
            "pollution_pressure",
            "human_welfare",
        ):
            frame = pd.read_csv(OUTPUT / f"{key}.csv")
            last = frame.dropna(subset=["observed"]).iloc[-1]
            self.assertAlmostEqual(last["observed"], last["forecast_median"], places=5)

    def test_sensitivity_envelope_contains_central_projection(self):
        for path in OUTPUT.glob("*.csv"):
            frame = pd.read_csv(path)
            if "forecast_median" not in frame:
                continue
            projected = frame.dropna(subset=["forecast_median"])
            self.assertTrue((projected["sensitivity_low"] <= projected["forecast_median"]).all())
            self.assertTrue((projected["forecast_median"] <= projected["sensitivity_high"]).all())

    def test_structural_alternative_is_exported(self):
        for path in OUTPUT.glob("*.csv"):
            frame = pd.read_csv(path)
            if "forecast_median" not in frame:
                continue
            projected = frame.dropna(subset=["forecast_median"])
            self.assertIn("alternate_bau", frame.columns)
            self.assertTrue(projected["alternate_bau"].notna().all())

    def test_original_bau_and_continuous_hybrid_are_exported(self):
        for key in (
            "population",
            "industry_per_capita",
            "food_per_capita",
            "pollution_pressure",
            "human_welfare",
        ):
            frame = pd.read_csv(OUTPUT / f"{key}.csv")
            self.assertTrue(frame["original_bau"].notna().all())
            observed_period = frame["observed"].notna()
            projected_period = frame["forecast_median"].notna()
            self.assertTrue(frame.loc[observed_period, "hybrid_2026"].notna().all())
            self.assertTrue(frame.loc[projected_period, "hybrid_2026"].notna().all())

    def test_pollution_mapping_is_flow_to_flow(self):
        manifest = __import__("json").loads((OUTPUT / "manifest.json").read_text())
        self.assertIn("flow-to-flow", manifest["pollution_mapping"])

    def test_recent_backtest_is_complete_and_finite(self):
        frame = pd.read_csv(OUTPUT / "backtest_2019_latest.csv")
        self.assertEqual(len(frame), 5)
        self.assertTrue(frame["bau2_e2026_mape_pct"].notna().all())
        self.assertTrue(frame["bau2_level_anchored_mape_pct"].notna().all())

    def test_multi_origin_backtest_has_no_future_selection(self):
        frame = pd.read_csv(OUTPUT / "backtest_multi_origin.csv")
        self.assertEqual(len(frame), 5)
        self.assertTrue((frame["n_origins"] == 4).all())
        self.assertTrue((frame["n"] >= 44).all())
        self.assertTrue(
            frame["selection_rule"].str.contains("ending at each origin").all()
        )

    def test_population_keeps_un_medium_as_external_benchmark(self):
        frame = pd.read_csv(OUTPUT / "population.csv").set_index("year")
        self.assertGreater(frame.loc[2100, "benchmark"], frame.loc[2100, "forecast_median"])


if __name__ == "__main__":
    unittest.main()
