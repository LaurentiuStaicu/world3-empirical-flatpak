"""Run and document the scenario-only EROI/net-energy extension."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from model.net_energy import SCENARIOS, run_named_scenarios


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "scenarios"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    frame = run_named_scenarios()
    frame.to_csv(OUTPUT / "net_energy_scenarios.csv", index=False, float_format="%.8g")

    # Application-compatible views. The legacy p10/p90 column names are used
    # only as storage slots; in the UI they are explicitly labelled as a
    # non-probabilistic structural range across the three named scenarios.
    indexed = {
        name: group.set_index("year")
        for name, group in frame.groupby("scenario", sort=False)
    }
    for metric in ("system_eroi", "net_energy_index"):
        central = indexed["quality_decline"][metric]
        accelerated = indexed["accelerated_transition"][metric]
        stress = indexed["fossil_lock_in_stress"][metric]
        values = pd.concat([central, accelerated, stress], axis=1)
        app_frame = pd.DataFrame(
            {
                "year": central.index.astype(int),
                "observed": float("nan"),
                "original_bau2": float("nan"),
                "fitted": float("nan"),
                "forecast_median": central.to_numpy(),
                "p10": values.min(axis=1).to_numpy(),
                "p90": values.max(axis=1).to_numpy(),
                "alternate_bau": accelerated.to_numpy(),
                "sensitivity_low": values.min(axis=1).to_numpy(),
                "sensitivity_high": values.max(axis=1).to_numpy(),
                "benchmark": float("nan"),
            }
        )
        app_frame.to_csv(OUTPUT / f"{metric}.csv", index=False, float_format="%.8g")

    selected = frame[frame["year"].isin([2025, 2030, 2035, 2050, 2100])]
    summary = selected[
        [
            "scenario",
            "year",
            "system_eroi",
            "energy_reinvestment_pct",
            "net_energy_index",
            "fossil_share",
            "fossil_resource_fraction",
        ]
    ]
    summary.to_csv(OUTPUT / "summary_years.csv", index=False, float_format="%.6g")

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    labels = {
        "quality_decline": "declinul calității",
        "accelerated_transition": "tranziție accelerată",
        "fossil_lock_in_stress": "stres fosil",
    }
    for scenario, group in frame.groupby("scenario", sort=False):
        axes[0].plot(group["year"], group["system_eroi"], label=labels[scenario])
        axes[1].plot(group["year"], group["net_energy_index"], label=labels[scenario])
    axes[0].set_ylabel("EROI sistemic")
    axes[1].set_ylabel("Energie netă (2025=100)")
    axes[1].set_xlabel("An")
    axes[0].legend(frameon=False)
    for axis in axes:
        axis.grid(alpha=0.25)
    fig.suptitle("Extensie dinamică energie netă — scenarii structurale, necalibrate")
    fig.tight_layout()
    fig.savefig(OUTPUT / "net_energy_scenarios.png", dpi=180)
    plt.close(fig)

    manifest = {
        "module": "net_energy_eroi",
        "version": "0.5.0",
        "status": "scenario_only_not_empirically_calibrated",
        "identity": "net = gross * (1 - 1 / EROI_system)",
        "mixing_rule": "1 / EROI_system = sum(source_share / source_EROI)",
        "scenarios": {name: vars(parameters) for name, parameters in SCENARIOS.items()},
        "current_anchors": [
            {
                "source": "Energy Institute Statistical Review of World Energy 2026",
                "coverage": "full-year global energy data through 2025",
                "url": "https://www.energyinst.org/statistical-review",
                "use": "future historical calibration target; not embedded in this run",
            },
            {
                "source": "IEA Key Questions on Energy and AI (2026)",
                "values": {"data_centres_twh_2025": 485, "data_centres_twh_2030": 950},
                "url": "https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary",
                "use": "future AI demand submodule; not a system-EROI observation",
            },
        ],
        "important_limit": (
            "Global EROI has no single homogeneous observed series. Parameter ranges are "
            "structural priors and must not be presented as probabilities or observations."
        ),
    }
    (OUTPUT / "net_energy_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
