"""Backtest a production-weighted regional climate-to-food bridge.

The prospective branch uses only information available at each forecast
origin.  A separate conditional branch uses subsequently observed climate and
is reported as a mechanism/nowcast diagnostic, never as a genuine forecast.
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
PANEL_PATH = ROOT / "data" / "processed" / "regional_cereal_climate_panel_2026.csv"
OUTPUT = ROOT / "outputs" / "regional_agricultural_stress"
ORIGINS = (2005, 2010, 2015, 2019)
DEVELOPMENT_ORIGINS = ORIGINS[:-1]
HOLDOUT_ORIGIN = ORIGINS[-1]
HORIZON = 5
CLIMATE_NORMAL_WINDOW = 20
PRODUCTION_WEIGHT_WINDOW = 10
RESPONSE_WINDOW = 20
MIN_CLIMATE_OBSERVATIONS = 15
RIDGE_PENALTY = 0.10
BETA_LOWER = -0.15
BETA_UPPER = 0.0
TEMPERATURE_SLOPE_LOWER = -0.05
TEMPERATURE_SLOPE_UPPER = 0.10


def log_rmse(observed: pd.Series, predicted: pd.Series) -> float:
    error = np.log(predicted.to_numpy(dtype=float) / observed.to_numpy(dtype=float))
    return float(np.sqrt(np.mean(np.square(error))))


def selected_candidate_id(candidates, indicators, origin: int) -> int:
    segments = tuple(segment for segment in VALIDATION_SEGMENTS if segment[1] <= origin)
    if not segments:
        return 0
    ranking = select_candidates(candidates, indicators, origin, segments)
    admissible = ranking.loc[ranking["mapping_boundary_count"].eq(0)]
    selected = admissible if not admissible.empty else ranking
    return int(selected.iloc[0]["candidate_id"])


def origin_country_parameters(panel: pd.DataFrame, origin: int) -> pd.DataFrame:
    """Estimate fixed country weights and climate normals through ``origin``."""
    climate_start = origin - CLIMATE_NORMAL_WINDOW + 1
    weight_start = origin - PRODUCTION_WEIGHT_WINDOW + 1
    history = panel.loc[
        (panel["year"] >= climate_start) & (panel["year"] <= origin)
    ].copy()
    grouped = history.groupby("code")
    stats = grouped.agg(
        climate_n=("year", "nunique"),
        temperature_mean=("temperature_anomaly_c_1991_2020", "mean"),
        temperature_sd=("temperature_anomaly_c_1991_2020", "std"),
        precipitation_mean=("precipitation_anomaly_mm_1991_2020", "mean"),
        precipitation_sd=("precipitation_anomaly_mm_1991_2020", "std"),
    )
    weights = (
        panel.loc[
            (panel["year"] >= weight_start) & (panel["year"] <= origin)
        ]
        .groupby("code")["cereal_production_tonnes"]
        .mean()
        .rename("production_weight_raw")
    )
    all_mapped_weight = float(weights.sum())
    stats = stats.join(weights, how="inner")
    stats = stats.loc[
        (stats["climate_n"] >= MIN_CLIMATE_OBSERVATIONS)
        & (stats["temperature_sd"] > 0.05)
        & (stats["precipitation_sd"] > 5.0)
        & (stats["production_weight_raw"] > 0)
    ].copy()
    if len(stats) < 100:
        raise ValueError(f"Only {len(stats)} countries are usable at origin {origin}")
    eligible_share = float(stats["production_weight_raw"].sum() / all_mapped_weight)
    stats["weight"] = stats["production_weight_raw"] / stats[
        "production_weight_raw"
    ].sum()
    stats["eligible_production_share"] = eligible_share
    return stats


def weighted_stress(
    observations: pd.DataFrame, stats: pd.DataFrame
) -> pd.Series:
    """Return a production-weighted hot-and-dry stress index by year."""
    merged = observations.merge(
        stats.reset_index(), on="code", how="inner", validate="many_to_one"
    )
    merged["hot_z"] = np.maximum(
        (
            merged["temperature_anomaly_c_1991_2020"]
            - merged["temperature_mean"]
        )
        / merged["temperature_sd"],
        0.0,
    )
    merged["dry_z"] = np.maximum(
        -(
            merged["precipitation_anomaly_mm_1991_2020"]
            - merged["precipitation_mean"]
        )
        / merged["precipitation_sd"],
        0.0,
    )
    merged["weighted_stress"] = merged["weight"] * 0.5 * (
        merged["hot_z"] + merged["dry_z"]
    )
    numerator = merged.groupby("year")["weighted_stress"].sum()
    denominator = merged.groupby("year")["weight"].sum()
    return (numerator / denominator).sort_index()


def prospective_country_climate(
    panel: pd.DataFrame, stats: pd.DataFrame, origin: int, years: pd.Index
) -> tuple[pd.DataFrame, int]:
    """Forecast country climate from pre-origin trends and mean reversion."""
    rows: list[dict[str, float | int | str]] = []
    trend_start = origin - CLIMATE_NORMAL_WINDOW + 1
    history = panel.loc[
        (panel["code"].isin(stats.index))
        & (panel["year"] >= trend_start)
        & (panel["year"] <= origin)
    ]
    latest_training_year = int(history["year"].max())
    for code, country in history.groupby("code"):
        if country["year"].nunique() < MIN_CLIMATE_OBSERVATIONS:
            continue
        x = country["year"].to_numpy(dtype=float)
        temperature = country["temperature_anomaly_c_1991_2020"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, temperature, 1)
        slope = float(
            np.clip(slope, TEMPERATURE_SLOPE_LOWER, TEMPERATURE_SLOPE_UPPER)
        )
        fitted_origin = float(intercept + slope * origin)
        precipitation_recent = country.loc[
            country["year"] >= origin - PRODUCTION_WEIGHT_WINDOW + 1,
            "precipitation_anomaly_mm_1991_2020",
        ]
        precipitation_forecast = float(precipitation_recent.mean())
        for year in years:
            rows.append(
                {
                    "code": code,
                    "year": int(year),
                    "temperature_anomaly_c_1991_2020": fitted_origin
                    + slope * (int(year) - origin),
                    "precipitation_anomaly_mm_1991_2020": precipitation_forecast,
                }
            )
    return pd.DataFrame(rows), latest_training_year


def response_coefficient(
    observed: pd.Series,
    base: pd.Series,
    stress: pd.Series,
    origin: int,
) -> float:
    overlap = observed.index.intersection(base.index).intersection(stress.index)
    overlap = overlap[(overlap >= origin - RESPONSE_WINDOW + 1) & (overlap <= origin)]
    residual_change = np.log(observed.loc[overlap] / base.loc[overlap]).diff().dropna()
    stress_change = stress.loc[overlap].diff().reindex(residual_change.index)
    valid = residual_change.notna() & stress_change.notna()
    x = stress_change.loc[valid]
    y = residual_change.loc[valid]
    beta = float((x * y).sum() / ((x * x).sum() + RIDGE_PENALTY))
    return float(np.clip(beta, BETA_LOWER, BETA_UPPER))


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
    panel = pd.read_csv(PANEL_PATH)
    indicators, _ = build_indicators()
    food = {indicator.key: indicator for indicator in indicators}["food_per_capita"]
    candidates = run_candidates(parameter_candidates())
    bridged = apply_observation_bridges(candidates)
    records: list[dict[str, float | int]] = []

    for origin in ORIGINS:
        candidate_id = selected_candidate_id(candidates, indicators, origin)
        candidate = bridged[candidate_id]
        _, _, scales, _ = score_candidate(candidate, indicators, origin)
        base = scales["food_per_capita"] * candidate.simulation["food_per_capita"]
        stats = origin_country_parameters(panel, origin)
        history = panel.loc[
            (panel["year"] >= origin - RESPONSE_WINDOW + 1)
            & (panel["year"] <= origin)
        ]
        historical_stress = weighted_stress(history, stats)
        beta = response_coefficient(food.observed, base, historical_stress, origin)

        observed = food.observed.loc[
            (food.observed.index > origin)
            & (food.observed.index <= origin + HORIZON)
        ].dropna()
        years = observed.index
        base_prediction = base.reindex(years)
        stress_origin = float(historical_stress.loc[origin])

        realized_climate = panel.loc[panel["year"].isin(years)]
        realized_stress = weighted_stress(realized_climate, stats).reindex(years)
        conditional_prediction = base_prediction * np.exp(
            beta * (realized_stress - stress_origin)
        )

        forecast_climate, climate_training_end = prospective_country_climate(
            panel, stats, origin, years
        )
        forecast_stress = weighted_stress(forecast_climate, stats).reindex(years)
        prospective_prediction = base_prediction * np.exp(
            beta * (forecast_stress - stress_origin)
        )
        persistence = pd.Series(float(food.observed.loc[origin]), index=years)
        records.append(
            {
                "origin": origin,
                "test_start": int(years.min()),
                "test_end": int(years.max()),
                "n": int(len(years)),
                "candidate_id": candidate_id,
                "country_count": int(len(stats)),
                "eligible_production_share": float(
                    stats["eligible_production_share"].iloc[0]
                ),
                "food_training_end": origin,
                "climate_training_end": climate_training_end,
                "weight_training_end": origin,
                "food_residual_response_per_stress_z": beta,
                "stress_at_origin": stress_origin,
                "realized_stress_test_mean": float(realized_stress.mean()),
                "forecast_stress_test_mean": float(forecast_stress.mean()),
                "persistence_log_rmse": log_rmse(observed, persistence),
                "existing_bridge_log_rmse": log_rmse(observed, base_prediction),
                "conditional_observed_climate_log_rmse": log_rmse(
                    observed, conditional_prediction
                ),
                "prospective_climate_log_rmse": log_rmse(
                    observed, prospective_prediction
                ),
            }
        )

    results = pd.DataFrame.from_records(records)
    results.to_csv(OUTPUT / "regional_stress_backtest.csv", index=False)
    summary_rows = []
    for period, origins in (
        ("development_pre2019", DEVELOPMENT_ORIGINS),
        ("independent_2019_2024", (HOLDOUT_ORIGIN,)),
        ("all_origins", ORIGINS),
    ):
        row: dict[str, float | str] = {
            "period": period,
            "origins": "/".join(str(origin) for origin in origins),
        }
        for column in (
            "persistence_log_rmse",
            "existing_bridge_log_rmse",
            "conditional_observed_climate_log_rmse",
            "prospective_climate_log_rmse",
        ):
            row[column] = pooled_rmse(results, column, origins)
        row["prospective_improvement_pct"] = 100.0 * (
            float(row["existing_bridge_log_rmse"])
            - float(row["prospective_climate_log_rmse"])
        ) / float(row["existing_bridge_log_rmse"])
        row["conditional_improvement_pct"] = 100.0 * (
            float(row["existing_bridge_log_rmse"])
            - float(row["conditional_observed_climate_log_rmse"])
        ) / float(row["existing_bridge_log_rmse"])
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUTPUT / "regional_stress_summary.csv", index=False)

    development = summary.loc[summary["period"].eq("development_pre2019")].iloc[0]
    holdout = summary.loc[summary["period"].eq("independent_2019_2024")].iloc[0]
    accepted = bool(
        development["prospective_climate_log_rmse"]
        < development["existing_bridge_log_rmse"]
        and holdout["prospective_climate_log_rmse"]
        < holdout["existing_bridge_log_rmse"]
    )
    manifest = {
        "module": "production_weighted_regional_climate_to_food_bridge",
        "status": "empirical_screening",
        "accepted": accepted,
        "production_decision": (
            "eligible_for_dynamic_feedback_design"
            if accepted
            else "keep_outside_bau_hybrid_2026_central_projection"
        ),
        "panel": (
            "FAOSTAT country cereal production joined to annual country "
            "temperature and precipitation anomalies from ERA5 processed by OWID"
        ),
        "origins": list(ORIGINS),
        "horizon_years": HORIZON,
        "development_origins": list(DEVELOPMENT_ORIGINS),
        "independent_holdout_origin": HOLDOUT_ORIGIN,
        "acceptance_rule": (
            "The genuinely prospective regional bridge must beat the existing "
            "BAU Hybrid food bridge both over pre-2019 development origins and "
            "the untouched 2019-2024 holdout."
        ),
        "future_data_control": (
            "At each origin, country weights, climate normals, response and "
            "country climate forecasts use only years through the origin. "
            "The observed-climate branch is explicitly conditional and is not "
            "used for the integration decision."
        ),
        "stress_definition": (
            "Ten-year trailing cereal-production weights; positive hot and dry "
            "country anomalies standardized against the preceding 20 years; "
            "equal heat and dryness weights."
        ),
        "prospective_climate_model": (
            "Country temperature uses a clipped 20-year linear trend; country "
            "precipitation uses the trailing ten-year mean."
        ),
        "important_limit": (
            "Annual country averages still omit crop calendars, within-country "
            "extremes, soil moisture, irrigation, adaptation, crop composition "
            "and trade reallocation."
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
