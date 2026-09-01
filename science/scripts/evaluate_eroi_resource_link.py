"""Backtest whether World3 resource depletion predicts observed fossil EROI."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from build_joint_hybrid_2026 import YEARS


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "energy_coupling"
DATA = ROOT / "data" / "processed" / "aramendia_global_fossil_eroi_2024.csv"
ORIGINS = (1995, 2000, 2005, 2010, 2015)
HORIZON = 5
BOUNDARIES = {
    "primary": "fossil_primary_eroi_including_indirect",
    "final": "fossil_final_eroi_including_indirect",
    "useful": "fossil_useful_eroi_including_indirect",
}


def resource_prediction(
    resource_train: np.ndarray,
    eroi_train: np.ndarray,
    resource_test: np.ndarray,
    resource_origin: float,
) -> np.ndarray:
    """Fit floor + scale * (resource/resource_at_origin)^elasticity."""

    ceiling = max(float(np.max(eroi_train)), 30.0)

    def predict(parameters: np.ndarray, resource: np.ndarray) -> np.ndarray:
        floor, scale, elasticity = parameters
        return floor + scale * (resource / resource_origin) ** elasticity

    initial = np.array([1.01, max(float(eroi_train[-1]) - 1.01, 0.1), 2.0])
    fitted = least_squares(
        lambda parameters: predict(parameters, resource_train) - eroi_train,
        initial,
        bounds=([1.001, 0.0, 0.01], [ceiling, 100.0, 20.0]),
    )
    return predict(fitted.x, resource_test)


def main() -> None:
    observed = pd.read_csv(DATA).set_index("year")
    simulations = np.load(OUTPUT.parent / "joint_hybrid_2026" / "candidate_simulations.npz")
    resources = pd.Series(
        simulations["series_resources_remaining_pct"][114] / 100.0,
        index=YEARS.astype(int),
    )
    records = []
    for boundary, column in BOUNDARIES.items():
        series = observed[column]
        for origin in ORIGINS:
            train_years = series.index[series.index <= origin]
            test_years = series.index[
                (series.index > origin) & (series.index <= origin + HORIZON)
            ]
            actual = series.loc[test_years].to_numpy(dtype=float)
            predictions = {
                "persistence": np.repeat(float(series.loc[origin]), len(test_years)),
                "linear_time": np.polyval(
                    np.polyfit(train_years, series.loc[train_years], 1), test_years
                ),
                "world3_resource_link": resource_prediction(
                    resources.loc[train_years].to_numpy(dtype=float),
                    series.loc[train_years].to_numpy(dtype=float),
                    resources.loc[test_years].to_numpy(dtype=float),
                    float(resources.loc[origin]),
                ),
            }
            for model, prediction in predictions.items():
                error = prediction - actual
                records.append(
                    {
                        "boundary": boundary,
                        "origin": origin,
                        "horizon": HORIZON,
                        "model": model,
                        "rmse": float(np.sqrt(np.mean(error**2))),
                        "mae": float(np.mean(np.abs(error))),
                    }
                )

    backtest = pd.DataFrame(records)
    summary = (
        backtest.groupby(["boundary", "model"], as_index=False)[["rmse", "mae"]]
        .mean()
        .sort_values(["boundary", "rmse"])
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    backtest.to_csv(OUTPUT / "eroi_resource_link_backtest.csv", index=False)
    summary.to_csv(OUTPUT / "eroi_resource_link_summary.csv", index=False)

    pivot = summary.pivot(index="boundary", columns="model", values="rmse")
    accepted = bool(
        (
            pivot["world3_resource_link"]
            < pivot["persistence"]
        ).all()
    )
    manifest = {
        "test": "world3_resource_fraction_to_fossil_eroi",
        "origins": list(ORIGINS),
        "horizon_years": HORIZON,
        "accepted": accepted,
        "acceptance_rule": (
            "The World3 resource link must beat persistence RMSE at primary, final "
            "and useful accounting boundaries."
        ),
        "production_consequence": (
            "Keep EROI/resource coupling outside BAU Hybrid 2026 central projection."
            if not accepted
            else "Eligible for the next joint calibration stage."
        ),
    }
    (OUTPUT / "eroi_resource_link_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(summary.to_string(index=False))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
