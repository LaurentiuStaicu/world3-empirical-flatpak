"""Compare observed series with World3 without fitting parameters."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from world3_empirical import run_scenario


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "empirical_model_inputs_2026-08-28.csv"
OUTPUT = ROOT / "outputs"


def normalize(series: pd.Series, years: pd.Series, base_year: int = 2010) -> pd.Series:
    base = float(series.loc[years.eq(base_year)].iloc[0])
    return 100 * series / base


def main() -> None:
    empirical = pd.read_csv(DATA)
    empirical = empirical.loc[empirical["year"].between(1960, 2024)].copy()
    model = run_scenario("world3_standard", year_min=1900, year_max=2024).annual().copy()
    model = model.loc[model["year"].between(1960, 2024)].copy()

    comparisons = [
        ("population", "population", "Population"),
        ("industrial_output", "industrial_output", "Industrial output proxy"),
        ("food_per_capita_proxy_index", "food_per_capita", "Food per capita proxy"),
        ("fossil_co2_proxy", "persistent_pollution", "CO2 flow vs pollution stock proxy"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    records = []
    for axis, (observed_name, model_name, label) in zip(axes.flat, comparisons):
        observed = empirical[["year", observed_name]].dropna()
        modeled = model[["year", model_name]].dropna()
        start = max(int(observed["year"].min()), int(modeled["year"].min()), 1960)
        base_year = 2010 if 2010 >= start else start
        observed_index = normalize(observed[observed_name], observed["year"], base_year)
        modeled_index = normalize(modeled[model_name], modeled["year"], base_year)
        axis.plot(observed["year"], observed_index, label="observed proxy", linewidth=2)
        axis.plot(modeled["year"], modeled_index, label="World3 standard", linewidth=2)
        axis.axvspan(2010, 2018, alpha=0.08, color="green", label="calibration window")
        axis.axvspan(2019, 2024, alpha=0.08, color="orange", label="test window")
        axis.set_title(label)
        axis.set_ylabel(f"Index, {base_year}=100")
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
        overlap = observed.loc[observed["year"].between(2019, 2024)].copy()
        predicted = np.interp(overlap["year"], modeled["year"], modeled_index)
        actual = observed_index.loc[overlap.index].to_numpy()
        for year, actual_value, predicted_value in zip(overlap["year"], actual, predicted):
            records.append(
                {
                    "variable": label,
                    "year": int(year),
                    "observed_index": float(actual_value),
                    "model_index": float(predicted_value),
                    "difference": float(predicted_value - actual_value),
                }
            )
    fig.suptitle("Uncalibrated empirical comparison: World3 standard", fontsize=15)
    fig.savefig(OUTPUT / "uncalibrated_empirical_comparison.png", dpi=180)
    pd.DataFrame(records).to_csv(OUTPUT / "uncalibrated_holdout_differences.csv", index=False)
    print(f"Saved empirical comparison to {OUTPUT}")


if __name__ == "__main__":
    main()
