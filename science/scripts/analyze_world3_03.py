"""Audit official World3-03 BAU/BAU2 against observed global proxies."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from world3_empirical.metrics import direction_accuracy, mape, rmse


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"
EMPIRICAL = ROOT / "data" / "processed" / "empirical_model_inputs_2026-08-28.csv"


def indexed(frame: pd.DataFrame, value: str, base_year: int = 2010) -> pd.Series:
    base = float(frame.loc[frame["year"].eq(base_year), value].iloc[0])
    return 100 * frame[value] / base


def main() -> None:
    observed = pd.read_csv(EMPIRICAL)
    scenarios = {
        "World3-03 BAU": pd.read_csv(OUTPUT / "world3_03_bau.csv"),
        "World3-03 BAU2": pd.read_csv(OUTPUT / "world3_03_bau2.csv"),
    }
    mappings = [
        ("population", "population", "Population", "eligible_provisional"),
        ("industrial_output", "industrial_output", "Industrial output proxy", "eligible_provisional"),
        ("food_per_capita_proxy_index", "food_per_capita", "Food per capita proxy", "excluded_data_quality"),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(13, 12), constrained_layout=True)
    metrics = []
    for row, (observed_name, model_name, label, status) in enumerate(mappings):
        observed_subset = observed[["year", observed_name]].dropna().copy()
        observed_subset["index"] = indexed(observed_subset, observed_name)
        for column, (scenario_name, model) in enumerate(scenarios.items()):
            model = model.loc[model["year"].between(observed_subset["year"].min(), 2035)].copy()
            model["index"] = indexed(model, model_name)
            axis = axes[row, column]
            axis.plot(observed_subset["year"], observed_subset["index"], label="Observed proxy", linewidth=2)
            axis.plot(model["year"], model["index"], label=scenario_name, linewidth=2)
            axis.axvspan(2019, 2024, alpha=0.1, color="orange", label="Holdout 2019–2024")
            axis.axvspan(2025, 2035, alpha=0.08, color="red", label="Scenario window")
            axis.set_title(f"{label}: {scenario_name}")
            axis.set_ylabel("Index, 2010=100")
            axis.grid(alpha=0.25)
            axis.legend(fontsize=8)

            for split, start, end in (("train", 2010, 2018), ("test", 2019, 2024)):
                sample = observed_subset.loc[observed_subset["year"].between(start, end)].copy()
                predicted = np.interp(sample["year"], model["year"], model["index"])
                actual = sample["index"].to_numpy()
                metrics.append(
                    {
                        "scenario": scenario_name,
                        "variable": label,
                        "calibration_status": status,
                        "split": split,
                        "n": len(sample),
                        "rmse_index_points": rmse(actual, predicted) if len(sample) else np.nan,
                        "mape_pct": mape(actual, predicted) if len(sample) else np.nan,
                        "direction_accuracy": direction_accuracy(actual, predicted) if len(sample) > 1 else np.nan,
                    }
                )

    fig.suptitle("Official World3-03 scenarios versus observed proxies", fontsize=15)
    fig.savefig(OUTPUT / "world3_03_empirical_audit.png", dpi=180)
    plt.close(fig)
    pd.DataFrame(metrics).to_csv(OUTPUT / "world3_03_empirical_metrics.csv", index=False)

    indicators = []
    for scenario_name, model in scenarios.items():
        baseline = model.loc[model["year"].eq(2025)].iloc[0]
        for year in (2025, 2030, 2035):
            row_data = model.loc[model["year"].eq(year)].iloc[0]
            for variable in (
                "population",
                "industrial_output_per_capita",
                "food_per_capita",
                "persistent_pollution_index",
                "human_welfare_index",
            ):
                indicators.append(
                    {
                        "scenario": scenario_name,
                        "year": year,
                        "variable": variable,
                        "value": float(row_data[variable]),
                        "change_from_2025_pct": float(100 * (row_data[variable] / baseline[variable] - 1)),
                    }
                )
    pd.DataFrame(indicators).to_csv(OUTPUT / "world3_03_2025_2035_indicators.csv", index=False)
    print(f"Saved World3-03 empirical audit and 2025–2035 indicators in {OUTPUT}")


if __name__ == "__main__":
    main()

