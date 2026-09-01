"""Generate baseline CSV files, comparison chart, and peak table."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from world3_empirical import run_scenario


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"
OUTPUT.mkdir(exist_ok=True)

scenarios = ["world3_standard", "bau2_structural_proxy"]
results = {name: run_scenario(name) for name in scenarios}
for name, result in results.items():
    result.annual().to_csv(OUTPUT / f"{name}.csv", index=False)

variables = [
    "population",
    "industrial_output_per_capita",
    "food_per_capita",
    "persistent_pollution_index",
    "nonrenewable_resource_fraction",
]
fig, axes = plt.subplots(3, 2, figsize=(13, 12), constrained_layout=True)
for axis, variable in zip(axes.flat, variables):
    for name, result in results.items():
        axis.plot(result.frame["year"], result.frame[variable], label=name)
    axis.set_title(variable.replace("_", " ").title())
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)
axes.flat[-1].axis("off")
fig.suptitle("World3 standard vs BAU2 structural proxy", fontsize=15)
fig.savefig(OUTPUT / "baseline_comparison.png", dpi=180)
plt.close(fig)

peak_records = []
for name, result in results.items():
    for variable in ("population", "industrial_output_per_capita", "food_per_capita", "persistent_pollution_index"):
        peak_records.append({"scenario": name, "variable": variable, "peak_year": result.peak_year(variable, 1950)})
pd.DataFrame(peak_records).to_csv(OUTPUT / "peak_years.csv", index=False)
print(f"Generated baseline artifacts in {OUTPUT}")

