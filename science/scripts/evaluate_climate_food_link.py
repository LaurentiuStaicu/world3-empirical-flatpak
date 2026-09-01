"""Test an incremental temperature-to-food link without future-data leakage.

The test starts from the existing BAU Hybrid food observation bridge.  At each
forecast origin, it selects the World3 candidate using only data available by
that origin, estimates a conservative response of the bridge residual to
annual temperature changes, and extrapolates temperature using only the prior
20 years.  Realized post-origin temperatures are never used as predictors.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_bau2_e2026 import build_indicators
from build_joint_hybrid_2026 import (
    VALIDATION_SEGMENTS,
    apply_observation_bridges,
    parameter_candidates,
    run_candidates,
    score_candidate,
    select_candidates,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "climate_food"
TEMPERATURE = ROOT / "data" / "processed" / "nasa_gistemp_global_2026.csv"
ORIGINS = (1995, 2000, 2005, 2010, 2015, 2019)
HORIZON = 5
DEVELOPMENT_ORIGINS = ORIGINS[:-1]
HOLDOUT_ORIGIN = ORIGINS[-1]
RESPONSE_WINDOW = 20
TEMPERATURE_TREND_WINDOW = 20
RIDGE_PENALTY = 0.05
BETA_LOWER = -0.15
BETA_UPPER = 0.0
TREND_LOWER = 0.0
TREND_UPPER = 0.05


def log_rmse(observed: pd.Series, predicted: pd.Series) -> float:
    values = np.log(
        predicted.to_numpy(dtype=float) / observed.to_numpy(dtype=float)
    )
    return float(np.sqrt(np.mean(np.square(values))))


def selected_candidate_id(candidates, indicators, origin: int) -> int:
    segments = tuple(segment for segment in VALIDATION_SEGMENTS if segment[1] <= origin)
    if not segments:
        return 0
    ranking = select_candidates(candidates, indicators, origin, segments)
    admissible = ranking.loc[ranking["mapping_boundary_count"].eq(0)]
    selected = admissible if not admissible.empty else ranking
    return int(selected.iloc[0]["candidate_id"])


def climate_parameters(
    observed: pd.Series,
    base: pd.Series,
    temperature: pd.Series,
    origin: int,
) -> tuple[float, float, int]:
    training = observed.loc[observed.index <= origin].dropna()
    overlap = training.index.intersection(base.index).intersection(temperature.index)
    residual = np.log(training.loc[overlap] / base.loc[overlap])
    residual_change = residual.diff().dropna()
    temperature_change = temperature.loc[overlap].diff().reindex(residual_change.index)
    response_start = origin - RESPONSE_WINDOW + 1
    response_index = residual_change.index[residual_change.index >= response_start]
    y = residual_change.reindex(response_index).dropna()
    x = temperature_change.reindex(y.index)
    beta = float((x * y).sum() / ((x * x).sum() + RIDGE_PENALTY))
    beta = float(np.clip(beta, BETA_LOWER, BETA_UPPER))

    trend_start = origin - TEMPERATURE_TREND_WINDOW + 1
    trend_data = temperature.loc[
        (temperature.index >= trend_start) & (temperature.index <= origin)
    ].dropna()
    if len(trend_data) < 10:
        raise ValueError(f"Insufficient temperature history at origin {origin}")
    slope = float(np.polyfit(trend_data.index, trend_data.to_numpy(dtype=float), 1)[0])
    slope = float(np.clip(slope, TREND_LOWER, TREND_UPPER))
    return beta, slope, int(trend_data.index.max())


def pooled_rmse(frame: pd.DataFrame, column: str, origins: tuple[int, ...]) -> float:
    selected = frame.loc[frame["origin"].isin(origins)]
    return float(
        np.sqrt(
            np.average(
                np.square(selected[column].to_numpy(dtype=float)),
                weights=selected["n"].to_numpy(dtype=float),
            )
        )
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    indicators, _ = build_indicators()
    by_key = {indicator.key: indicator for indicator in indicators}
    food = by_key["food_per_capita"]
    temperature = pd.read_csv(TEMPERATURE).set_index("year")[
        "temperature_anomaly_c_1951_1980"
    ]

    candidates = run_candidates(parameter_candidates())
    bridged = apply_observation_bridges(candidates)
    records: list[dict[str, float | int]] = []
    for origin in ORIGINS:
        candidate_id = selected_candidate_id(candidates, indicators, origin)
        candidate = bridged[candidate_id]
        _, _, scales, _ = score_candidate(candidate, indicators, origin)
        base = scales["food_per_capita"] * candidate.simulation["food_per_capita"]
        beta, temperature_slope, temperature_training_end = climate_parameters(
            food.observed, base, temperature, origin
        )

        observed = food.observed.loc[
            (food.observed.index > origin)
            & (food.observed.index <= origin + HORIZON)
        ].dropna()
        years = observed.index
        base_prediction = base.reindex(years)
        climate_prediction = base_prediction * np.exp(
            beta * temperature_slope * (years.to_numpy(dtype=float) - origin)
        )
        persistence = pd.Series(float(food.observed.loc[origin]), index=years)
        records.append(
            {
                "origin": origin,
                "test_start": int(years.min()),
                "test_end": int(years.max()),
                "n": int(len(years)),
                "candidate_id": candidate_id,
                "food_training_end": origin,
                "temperature_training_end": temperature_training_end,
                "temperature_slope_c_per_year": temperature_slope,
                "food_residual_response_per_c": beta,
                "persistence_log_rmse": log_rmse(observed, persistence),
                "existing_bridge_log_rmse": log_rmse(observed, base_prediction),
                "climate_bridge_log_rmse": log_rmse(observed, climate_prediction),
            }
        )

    results = pd.DataFrame.from_records(records)
    results["climate_improvement_pct"] = 100.0 * (
        results["existing_bridge_log_rmse"] - results["climate_bridge_log_rmse"]
    ) / results["existing_bridge_log_rmse"]
    results.to_csv(OUTPUT / "climate_food_backtest.csv", index=False)

    summary_rows = []
    for period, origins in (
        ("development_pre2019", DEVELOPMENT_ORIGINS),
        ("independent_2019_2024", (HOLDOUT_ORIGIN,)),
        ("all_origins", ORIGINS),
    ):
        persistence = pooled_rmse(results, "persistence_log_rmse", origins)
        existing = pooled_rmse(results, "existing_bridge_log_rmse", origins)
        climate = pooled_rmse(results, "climate_bridge_log_rmse", origins)
        summary_rows.append(
            {
                "period": period,
                "origins": "/".join(str(value) for value in origins),
                "persistence_log_rmse": persistence,
                "existing_bridge_log_rmse": existing,
                "climate_bridge_log_rmse": climate,
                "climate_improvement_pct": 100.0 * (existing - climate) / existing,
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUTPUT / "climate_food_summary.csv", index=False)

    development = summary.loc[summary["period"].eq("development_pre2019")].iloc[0]
    holdout = summary.loc[summary["period"].eq("independent_2019_2024")].iloc[0]
    accepted = bool(
        development["climate_bridge_log_rmse"]
        < development["existing_bridge_log_rmse"]
        and holdout["climate_bridge_log_rmse"]
        < holdout["existing_bridge_log_rmse"]
    )
    manifest = {
        "module": "temperature_to_food_incremental_bridge",
        "status": "empirical_screening",
        "accepted": accepted,
        "production_decision": (
            "eligible_for_dynamic_feedback_design"
            if accepted
            else "keep_outside_bau_hybrid_2026_central_projection"
        ),
        "temperature_dataset": "NASA GISTEMP v4 global LOTI, 1880-2025",
        "food_dataset": "FAOSTAT World Food gross per-capita production index",
        "origins": list(ORIGINS),
        "horizon_years": HORIZON,
        "development_origins": list(DEVELOPMENT_ORIGINS),
        "independent_holdout_origin": HOLDOUT_ORIGIN,
        "acceptance_rule": (
            "The climate bridge must beat the existing BAU Hybrid food bridge "
            "both across pre-2019 development origins and in the untouched "
            "2019-2024 holdout."
        ),
        "future_data_control": (
            "At each origin, post-origin temperatures are not used. Future "
            "temperature is a linear extrapolation fitted only to the preceding "
            "20 annual GISTEMP observations."
        ),
        "response_model": (
            "Ridge-regularized response of annual log food-bridge residual changes "
            "to annual temperature changes over the preceding 20 years; response "
            "constrained to [-0.15, 0] per degree C."
        ),
        "important_limit": (
            "Global mean temperature cannot represent regional heat, drought, "
            "soil moisture, irrigation or trade adaptation. Failure here rejects "
            "this simple global bridge, not climate impacts on agriculture."
        ),
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(results.to_string(index=False))
    print(summary.to_string(index=False))
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
