"""Run the official World3-03 BAU and BAU2 scenarios and make audit outputs."""

from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import pandas as pd

from world3_empirical.world3_03 import run_world3_03


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"
OUTPUT.mkdir(exist_ok=True)


def main() -> None:
    results = {}
    warning_records = []
    for number in (1, 2):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            results[number] = run_world3_03(number)
        lookup_warnings = [
            item
            for item in caught
            if item.category is UserWarning
            and str(item.filename).endswith("pysd/py_backend/lookups.py")
        ]
        for item in caught:
            if item not in lookup_warnings:
                warnings.warn_explicit(
                    item.message,
                    item.category,
                    item.filename,
                    item.lineno,
                )
        messages = [str(item.message) for item in lookup_warnings]
        warning_records.append(
            {
                "scenario": number,
                "total": len(messages),
                "above": sum("above the maximum" in value for value in messages),
                "below": sum("below the minimum" in value for value in messages),
                "unique": len(set(messages)),
            }
        )
        print(
            f"World3-03 scenario {number}; lookup extrapolations={len(messages)} "
            f"({len(set(messages))} unique)",
            flush=True,
        )
    for result in results.values():
        result.frame.to_csv(OUTPUT / f"{result.scenario_name}.csv", index=False)
    pd.DataFrame(warning_records).to_csv(
        OUTPUT / "world3_03_lookup_extrapolation_audit.csv", index=False
    )

    variables = [
        "population",
        "industrial_output_per_capita",
        "food_per_capita",
        "persistent_pollution_index",
        "nonrenewable_resource_fraction",
        "human_welfare_index",
    ]
    fig, axes = plt.subplots(3, 2, figsize=(13, 12), constrained_layout=True)
    for axis, variable in zip(axes.flat, variables):
        for result in results.values():
            axis.plot(result.frame["year"], result.frame[variable], label=result.scenario_name)
        axis.set_title(variable.replace("_", " ").title())
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    fig.suptitle("Official World3-03 scenarios: BAU vs BAU2", fontsize=15)
    fig.savefig(OUTPUT / "world3_03_bau_bau2_comparison.png", dpi=180)
    plt.close(fig)

    records = []
    for result in results.values():
        for variable in variables[:4]:
            records.append(
                {
                    "scenario": result.scenario_name,
                    "variable": variable,
                    "global_peak_year": result.peak_year(variable, 1950),
                }
            )
    pd.DataFrame(records).to_csv(OUTPUT / "world3_03_peak_years.csv", index=False)
    print(f"Generated official World3-03 artifacts in {OUTPUT}")


if __name__ == "__main__":
    main()
