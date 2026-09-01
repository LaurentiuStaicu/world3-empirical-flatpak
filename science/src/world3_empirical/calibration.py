"""Bounded calibration, temporal backtesting, and uncertainty propagation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import qmc

from .metrics import direction_accuracy, mape, rmse
from .model import run_scenario


@dataclass(frozen=True)
class CalibrationResult:
    parameters: dict[str, float]
    objective_cost: float
    success: bool
    message: str
    train_metrics: pd.DataFrame
    test_metrics: pd.DataFrame


def _validate_observations(observations: pd.DataFrame) -> None:
    required = {"year", "variable", "value", "split"}
    missing = required - set(observations.columns)
    if missing:
        raise ValueError(f"Observations are missing columns: {sorted(missing)}")
    invalid_splits = set(observations["split"]) - {"train", "test"}
    if invalid_splits:
        raise ValueError(f"Invalid split values: {sorted(invalid_splits)}")
    if (observations["value"] <= 0).any():
        raise ValueError("Log-residual calibration requires strictly positive observations")


def predictions_for(observations: pd.DataFrame, parameters: Mapping[str, float], scenario: str) -> np.ndarray:
    result = run_scenario(
        scenario,
        year_min=int(np.floor(observations["year"].min())),
        year_max=int(np.ceil(observations["year"].max())),
        extra_constants=parameters,
    ).frame
    predictions = np.empty(len(observations), dtype=float)
    for variable, positions in observations.groupby("variable").groups.items():
        if variable not in result:
            raise KeyError(f"Observation variable {variable!r} is not a model output")
        rows = observations.loc[positions]
        predictions[positions] = np.interp(rows["year"], result["year"], result[variable])
    return predictions


def _metric_table(observations: pd.DataFrame, predictions: np.ndarray, split: str) -> pd.DataFrame:
    subset = observations["split"].eq(split).to_numpy()
    records = []
    for variable in observations.loc[subset, "variable"].unique():
        selected = subset & observations["variable"].eq(variable).to_numpy()
        observed = observations.loc[selected, "value"].to_numpy()
        predicted = predictions[selected]
        records.append(
            {
                "variable": variable,
                "n": int(selected.sum()),
                "rmse": rmse(observed, predicted),
                "mape_pct": mape(observed, predicted),
                "direction_accuracy": direction_accuracy(observed, predicted),
            }
        )
    return pd.DataFrame.from_records(records)


def calibrate(
    observations: pd.DataFrame,
    parameter_bounds: Mapping[str, tuple[float, float]],
    *,
    scenario: str = "world3_standard",
    initial: Mapping[str, float] | None = None,
    max_nfev: int = 300,
) -> CalibrationResult:
    observations = observations.reset_index(drop=True).copy()
    _validate_observations(observations)
    names = list(parameter_bounds)
    lower = np.array([parameter_bounds[name][0] for name in names], dtype=float)
    upper = np.array([parameter_bounds[name][1] for name in names], dtype=float)
    if np.any(lower >= upper):
        raise ValueError("Every parameter lower bound must be below its upper bound")
    x0 = np.array(
        [initial.get(name, (lo + hi) / 2) if initial else (lo + hi) / 2 for name, lo, hi in zip(names, lower, upper)],
        dtype=float,
    )
    train = observations["split"].eq("train").to_numpy()

    def residuals(values: Sequence[float]) -> np.ndarray:
        parameters = dict(zip(names, values))
        predicted = predictions_for(observations, parameters, scenario)
        return np.log(predicted[train]) - np.log(observations.loc[train, "value"].to_numpy())

    fitted = least_squares(residuals, x0=x0, bounds=(lower, upper), max_nfev=max_nfev)
    parameters = dict(zip(names, fitted.x))
    predicted = predictions_for(observations, parameters, scenario)
    return CalibrationResult(
        parameters=parameters,
        objective_cost=float(fitted.cost),
        success=bool(fitted.success),
        message=str(fitted.message),
        train_metrics=_metric_table(observations, predicted, "train"),
        test_metrics=_metric_table(observations, predicted, "test"),
    )


def monte_carlo(
    parameter_bounds: Mapping[str, tuple[float, float]],
    *,
    scenario: str = "world3_standard",
    samples: int = 100,
    years: Sequence[int] = (2025, 2030, 2035),
    variables: Sequence[str] = ("population", "food_per_capita", "industrial_output_per_capita"),
    seed: int = 42,
) -> pd.DataFrame:
    names = list(parameter_bounds)
    lower = np.array([parameter_bounds[name][0] for name in names], dtype=float)
    upper = np.array([parameter_bounds[name][1] for name in names], dtype=float)
    design = qmc.LatinHypercube(d=len(names), seed=seed).random(samples)
    parameter_samples = qmc.scale(design, lower, upper)
    records: list[dict[str, float | int | str]] = []
    for sample_id, values in enumerate(parameter_samples):
        result = run_scenario(
            scenario,
            year_min=1900,
            year_max=max(years),
            extra_constants=dict(zip(names, values)),
        ).frame
        for year in years:
            for variable in variables:
                value = float(np.interp(year, result["year"], result[variable]))
                records.append({"sample": sample_id, "year": year, "variable": variable, "value": value})
    draws = pd.DataFrame.from_records(records)
    return (
        draws.groupby(["year", "variable"])["value"]
        .quantile([0.05, 0.5, 0.95])
        .unstack()
        .rename(columns={0.05: "p05", 0.5: "median", 0.95: "p95"})
        .reset_index()
    )

