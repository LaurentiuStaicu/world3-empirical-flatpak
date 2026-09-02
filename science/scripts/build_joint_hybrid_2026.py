"""Build a jointly calibrated BAU Hybrid 2026 trajectory.

Every displayed indicator comes from the same World3-03 scenario-2 run and
the same structural parameter vector.  Per-indicator constants are limited to
observation-unit mappings; they do not alter the simulated feedbacks.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import tempfile
import warnings

import numpy as np
import pandas as pd
import pysd
from pysd.py_backend.lookups import Lookups
from scipy.stats import qmc
import xarray as xr

from build_bau2_e2026 import Indicator, build_indicators
from world3_empirical.world3_03 import _sanitized_model_text, _source_model_path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "joint_hybrid_2026"
CACHE = OUTPUT / "candidate_simulations.npz"
YEARS = np.arange(1900, 2101, dtype=float)
MODEL_COLUMNS = [
    "population",
    "industrial_output",
    "industrial_output_per_capita",
    "food_per_capita",
    "persistent_pollution_generation_rate",
    "persistent_pollution",
    "fraction_of_resources_remaining",
    "human_welfare_index",
]
SIMULATION_KEYS = (
    "population",
    "industry_per_capita",
    "food_per_capita",
    "pollution_pressure",
    "human_welfare",
    "industry_total",
    "persistent_pollution_stock",
    "resources_remaining_pct",
)
SCALE_BOUNDS = {
    "population": (0.90, 1.15),
    "industry_per_capita": (0.50, 1.60),
    "food_per_capita": (0.50, 1.80),
    "pollution_pressure": (0.30, 2.00),
    "human_welfare": (0.50, 1.50),
}
VALIDATION_SEGMENTS = ((2005, 2009), (2010, 2014), (2015, 2018))
PRODUCTION_SEGMENTS = VALIDATION_SEGMENTS + ((2018, 2025),)
SELECTION_CUTOFF = 2018
CANDIDATE_COUNT = 128
ENSEMBLE_SIZE = 12
FOOD_WORLD3_WEIGHT = 0.25
POLLUTION_WORLD3_WEIGHT = 0.0
BRIDGE_WEIGHT_GRID = (1.0, 0.75, 0.50, 0.25, 0.0)
SNAPSHOT_DATE = "2026-08-30"


@dataclass(frozen=True)
class ParameterSpec:
    key: str
    model_name: str
    baseline: float
    lower: float
    upper: float


PARAMETERS = (
    ParameterSpec("resources", "initial nonrenewable resources", 2.0e12, 1.5e12, 3.5e12),
    ParameterSpec("industrial_output_ratio", "industrial capital output ratio 1", 3.0, 2.55, 3.45),
    ParameterSpec("industrial_capital_life", "average life of industrial capital 1", 14.0, 11.0, 18.0),
    ParameterSpec("land_yield", "land yield factor 1", 1.0, 0.82, 1.18),
    ParameterSpec("pollution_generation", "persistent pollution generation factor 1", 1.0, 0.65, 1.35),
    ParameterSpec("pollution_assimilation", "assimilation half life in 1970", 1.5, 1.0, 2.3),
    ParameterSpec("family_size", "desired completed family size normal", 3.8, 3.1, 4.4),
)


@dataclass
class Candidate:
    candidate_id: int
    values: np.ndarray
    simulation: dict[str, pd.Series]

    def parameters(self) -> dict[str, float]:
        return {spec.key: float(value) for spec, value in zip(PARAMETERS, self.values)}


def apply_observation_bridges(
    candidates: list[Candidate],
    *,
    food_world3_weight: float = FOOD_WORLD3_WEIGHT,
    pollution_world3_weight: float = POLLUTION_WORLD3_WEIGHT,
) -> list[Candidate]:
    """Map latent World3 outputs to two observed constructs.

    FAOSTAT food per capita is represented by a Cobb--Douglas-like observation
    operator combining World3's biophysical food signal with industrial input
    capacity. Annual CO2 is represented by industrial throughput rather than
    the non-equivalent World3 stock-pollution generation flow. Both drivers
    still come from one coupled World3 run; these bridges do not alter its
    stocks, feedbacks, or parameter selection.
    """
    bridged: list[Candidate] = []
    for candidate in candidates:
        simulation = dict(candidate.simulation)
        simulation["food_per_capita"] = np.exp(
            food_world3_weight * np.log(candidate.simulation["food_per_capita"])
            + (1.0 - food_world3_weight)
            * np.log(candidate.simulation["industry_per_capita"])
        )
        simulation["pollution_pressure"] = np.exp(
            pollution_world3_weight
            * np.log(candidate.simulation["pollution_pressure"])
            + (1.0 - pollution_world3_weight)
            * np.log(candidate.simulation["industry_total"])
        )
        bridged.append(Candidate(candidate.candidate_id, candidate.values, simulation))
    return bridged


def parameter_candidates(count: int = CANDIDATE_COUNT, seed: int = 20260829) -> np.ndarray:
    if count < 8:
        raise ValueError("Joint calibration requires at least eight candidates")
    lower = np.array([spec.lower for spec in PARAMETERS], dtype=float)
    upper = np.array([spec.upper for spec in PARAMETERS], dtype=float)
    design = qmc.LatinHypercube(d=len(PARAMETERS), seed=seed).random(count - 1)
    sampled = qmc.scale(design, lower, upper)
    baseline = np.array([spec.baseline for spec in PARAMETERS], dtype=float)
    return np.vstack([baseline, sampled])


def model_parameters(values: np.ndarray) -> dict[str, float]:
    params = {"scenario": 2.0}
    for spec, value in zip(PARAMETERS, values):
        params[spec.model_name] = float(value)
    # Scenario 2 normally selects 2e12 through a lookup.  The explicit custom
    # switch lets the resource prior vary while all other scenario-2 switches
    # remain untouched.
    params["initial nonrenewable resources use custom"] = 1.0
    return params


def transform_outputs(raw: pd.DataFrame) -> dict[str, pd.Series]:
    raw = raw.copy()
    raw.index = raw.index.astype(int)

    def indexed(column: str, base_year: int) -> pd.Series:
        series = raw[column].astype(float)
        return 100.0 * series / float(series.loc[base_year])

    return {
        "population": raw["population"].astype(float) / 1e9,
        "industry_per_capita": indexed("industrial_output_per_capita", 2015),
        "food_per_capita": indexed("food_per_capita", 2015),
        "pollution_pressure": indexed("persistent_pollution_generation_rate", 1990),
        "human_welfare": raw["human_welfare_index"].astype(float),
        "industry_total": indexed("industrial_output", 2015),
        "persistent_pollution_stock": indexed("persistent_pollution", 1990),
        "resources_remaining_pct": 100.0 * raw["fraction_of_resources_remaining"].astype(float),
    }


def parse_lookup_warning(message: str) -> tuple[str, str]:
    """Return the lookup identifier and boundary direction from a PySD warning."""
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError(f"Unexpected PySD lookup warning: {message!r}")
    lookup = lines[0]
    if "above the maximum" in lines[1]:
        direction = "above"
    elif "below the minimum" in lines[1]:
        direction = "below"
    else:
        raise ValueError(f"Unknown PySD lookup boundary direction: {message!r}")
    return lookup, direction


def lookup_extrapolation_measurement(
    lookup: Lookups, data: xr.DataArray, x: object
) -> dict[str, float | str] | None:
    """Describe one call that will emit a PySD lookup-boundary warning."""
    try:
        bounds = np.asarray(data["lookup_dim"].values, dtype=float)
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    if bounds.size < 2 or not np.isfinite(bounds).all():
        return None

    lower = float(bounds[0])
    upper = float(bounds[-1])
    if isinstance(x, xr.DataArray):
        if not x.dims:
            # PySD immediately recurses with a scalar and warns there.
            return None
        values = np.asarray(x.values, dtype=float)
        if lookup.interp != "extrapolate" and np.all(values > upper):
            direction = "above"
        elif lookup.interp != "extrapolate" and np.all(values < lower):
            direction = "below"
        else:
            # Mixed arrays are split by PySD; scalar recursive calls are audited.
            return None
    else:
        try:
            values = np.asarray([float(x)], dtype=float)
        except (TypeError, ValueError):
            return None
        if values[0] > upper:
            direction = "above"
        elif values[0] < lower:
            direction = "below"
        else:
            return None

    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    input_min = float(np.min(finite))
    input_max = float(np.max(finite))
    if direction == "above":
        nearest_distance = input_min - upper
        furthest_distance = input_max - upper
    else:
        nearest_distance = lower - input_max
        furthest_distance = lower - input_min
    span = upper - lower
    return {
        "lookup": lookup.py_name,
        "direction": direction,
        "input_min": input_min,
        "input_max": input_max,
        "lower_bound": lower,
        "upper_bound": upper,
        "nearest_boundary_distance": float(nearest_distance),
        "furthest_boundary_distance": float(furthest_distance),
        "nearest_boundary_distance_normalized": float(nearest_distance / span),
        "furthest_boundary_distance_normalized": float(furthest_distance / span),
    }


@contextmanager
def capture_lookup_extrapolation_context(model):
    """Capture time, input and domain for every warning emitted by PySD lookups."""
    original_call = Lookups._call
    aggregated: dict[tuple[str, str, float, float, float], dict[str, object]] = {}

    def audited_call(lookup, data, x, final_subs=None):
        measurement = lookup_extrapolation_measurement(lookup, data, x)
        if measurement is not None:
            year = float(model.time())
            key = (
                str(measurement["lookup"]),
                str(measurement["direction"]),
                year,
                float(measurement["lower_bound"]),
                float(measurement["upper_bound"]),
            )
            if key not in aggregated:
                aggregated[key] = {"year": year, "count": 0, **measurement}
            row = aggregated[key]
            row["count"] = int(row["count"]) + 1
            row["input_min"] = min(
                float(row["input_min"]), float(measurement["input_min"])
            )
            row["input_max"] = max(
                float(row["input_max"]), float(measurement["input_max"])
            )
            for name in (
                "nearest_boundary_distance",
                "nearest_boundary_distance_normalized",
            ):
                row[name] = min(float(row[name]), float(measurement[name]))
            for name in (
                "furthest_boundary_distance",
                "furthest_boundary_distance_normalized",
            ):
                row[name] = max(float(row[name]), float(measurement[name]))
        return original_call(lookup, data, x, final_subs)

    Lookups._call = audited_call
    try:
        yield aggregated
    finally:
        Lookups._call = original_call


def _run_candidate_chunk(
    tasks: list[tuple[int, np.ndarray]],
) -> list[tuple[int, np.ndarray, dict[str, np.ndarray], dict[str, object]]]:
    """Run one deterministic shard with one PySD model load per process."""
    results: list[
        tuple[int, np.ndarray, dict[str, np.ndarray], dict[str, object]]
    ] = []
    with tempfile.TemporaryDirectory(prefix="joint_world3_03_worker_") as directory:
        model_path = Path(directory) / "World3_03_Joint.mdl"
        model_path.write_text(_sanitized_model_text(_source_model_path()), encoding="utf-8")
        model = pysd.read_vensim(model_path)
        for candidate_id, values in tasks:
            with capture_lookup_extrapolation_context(model) as warning_context:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    raw = model.run(
                        params=model_parameters(values),
                        return_columns=MODEL_COLUMNS,
                        return_timestamps=YEARS,
                        reload=True,
                    )
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
            warning_messages = [str(item.message) for item in lookup_warnings]
            warning_details = Counter(
                "\t".join(parse_lookup_warning(message))
                for message in warning_messages
            )
            contextual_rows = list(warning_context.values())
            contextual_count = sum(int(row["count"]) for row in contextual_rows)
            if contextual_count != len(warning_messages):
                raise RuntimeError(
                    f"Candidate {candidate_id}: contextual lookup audit captured "
                    f"{contextual_count} events but PySD emitted "
                    f"{len(warning_messages)} warnings"
                )
            warning_stats = {
                "total": len(warning_messages),
                "above": sum("above the maximum" in value for value in warning_messages),
                "below": sum("below the minimum" in value for value in warning_messages),
                "unique": len(set(warning_messages)),
                "details": dict(warning_details),
                "context": contextual_rows,
            }
            if not np.isfinite(raw.to_numpy(dtype=float)).all():
                raise RuntimeError(f"Candidate {candidate_id} produced non-finite output")
            transformed = {
                key: value.reindex(YEARS.astype(int)).to_numpy(dtype=float)
                for key, value in transform_outputs(raw).items()
            }
            results.append((candidate_id, values, transformed, warning_stats))
            print(
                f"World3-03 candidate {candidate_id + 1}/{CANDIDATE_COUNT}; "
                f"lookup extrapolations={warning_stats['total']} "
                f"({warning_stats['unique']} unique)",
                flush=True,
            )
    return results


def export_lookup_warning_audit(stats: dict[int, dict[str, object]]) -> None:
    rows = []
    detail_rows = []
    context_rows = []
    for candidate_id in sorted(stats):
        row = {"candidate_id": candidate_id}
        row.update(
            {
                key: int(stats[candidate_id][key])
                for key in ("total", "above", "below", "unique")
            }
        )
        rows.append(row)
        details = stats[candidate_id]["details"]
        if not isinstance(details, dict):
            raise TypeError("Lookup warning details must be a dictionary")
        for compound, count in sorted(details.items()):
            lookup, direction = str(compound).split("\t", maxsplit=1)
            detail_rows.append(
                {
                    "candidate_id": candidate_id,
                    "lookup": lookup,
                    "direction": direction,
                    "count": int(count),
                }
            )
        context = stats[candidate_id]["context"]
        if not isinstance(context, list):
            raise TypeError("Lookup warning context must be a list")
        for contextual_row in context:
            if not isinstance(contextual_row, dict):
                raise TypeError("Each lookup warning context row must be a dictionary")
            context_rows.append({"candidate_id": candidate_id, **contextual_row})
    pd.DataFrame(rows).to_csv(
        OUTPUT / "lookup_extrapolation_audit.csv", index=False
    )
    pd.DataFrame(
        detail_rows,
        columns=("candidate_id", "lookup", "direction", "count"),
    ).to_csv(OUTPUT / "lookup_extrapolation_detail.csv", index=False)
    pd.DataFrame(
        context_rows,
        columns=(
            "candidate_id",
            "lookup",
            "direction",
            "year",
            "count",
            "input_min",
            "input_max",
            "lower_bound",
            "upper_bound",
            "nearest_boundary_distance",
            "furthest_boundary_distance",
            "nearest_boundary_distance_normalized",
            "furthest_boundary_distance_normalized",
        ),
    ).sort_values(
        ["candidate_id", "lookup", "direction", "year"]
    ).to_csv(OUTPUT / "lookup_extrapolation_context.csv", index=False)


def run_candidates(candidate_values: np.ndarray) -> list[Candidate]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if CACHE.exists():
        cached = np.load(CACHE)
        warning_keys = ("warning_total", "warning_above", "warning_below", "warning_unique")
        if (
            cached["values"].shape == candidate_values.shape
            and np.allclose(cached["values"], candidate_values)
            and all(key in cached for key in warning_keys)
            and "warning_details_json" in cached
            and "warning_context_json" in cached
        ):
            candidates = []
            for candidate_id, values in enumerate(candidate_values):
                simulation = {
                    key: pd.Series(
                        cached[f"series_{key}"][candidate_id],
                        index=YEARS.astype(int),
                        dtype=float,
                    )
                    for key in SIMULATION_KEYS
                }
                candidates.append(Candidate(candidate_id, values, simulation))
            export_lookup_warning_audit(
                {
                    candidate_id: {
                        **{
                            key.removeprefix("warning_"): int(cached[key][candidate_id])
                            for key in warning_keys
                        },
                        "details": json.loads(
                            str(cached["warning_details_json"][candidate_id])
                        ),
                        "context": json.loads(
                            str(cached["warning_context_json"][candidate_id])
                        ),
                    }
                    for candidate_id in range(len(candidate_values))
                }
            )
            print(f"Loaded {len(candidates)} cached World3-03 candidates", flush=True)
            return candidates

    worker_count = min(4, os.cpu_count() or 1, len(candidate_values))
    task_shards: list[list[tuple[int, np.ndarray]]] = [[] for _ in range(worker_count)]
    for candidate_id, values in enumerate(candidate_values):
        task_shards[candidate_id % worker_count].append((candidate_id, values))
    completed: dict[int, Candidate] = {}
    warning_stats: dict[int, dict[str, object]] = {}
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(_run_candidate_chunk, shard) for shard in task_shards]
        for future in as_completed(futures):
            for candidate_id, values, arrays, stats in future.result():
                simulation = {
                    key: pd.Series(value, index=YEARS.astype(int), dtype=float)
                    for key, value in arrays.items()
                }
                completed[candidate_id] = Candidate(candidate_id, values, simulation)
                warning_stats[candidate_id] = stats
    candidates = [completed[candidate_id] for candidate_id in range(len(candidate_values))]
    cache_payload: dict[str, np.ndarray] = {"values": candidate_values}
    for key in SIMULATION_KEYS:
        cache_payload[f"series_{key}"] = np.vstack(
            [candidate.simulation[key].reindex(YEARS.astype(int)).to_numpy(dtype=float) for candidate in candidates]
        )
    for key in ("total", "above", "below", "unique"):
        cache_payload[f"warning_{key}"] = np.array(
            [warning_stats[candidate_id][key] for candidate_id in range(len(candidates))],
            dtype=int,
        )
    cache_payload["warning_details_json"] = np.array(
        [
            json.dumps(warning_stats[candidate_id]["details"], sort_keys=True)
            for candidate_id in range(len(candidates))
        ],
        dtype=str,
    )
    cache_payload["warning_context_json"] = np.array(
        [
            json.dumps(warning_stats[candidate_id]["context"], sort_keys=True)
            for candidate_id in range(len(candidates))
        ],
        dtype=str,
    )
    np.savez_compressed(CACHE, **cache_payload)
    export_lookup_warning_audit(warning_stats)
    return candidates


def observation_mapping(
    indicator: Indicator, model: pd.Series, cutoff: int
) -> tuple[float, pd.Index]:
    observed = indicator.observed.dropna()
    overlap = observed.index.intersection(model.index)
    overlap = overlap[(overlap >= 1990) & (overlap <= cutoff)]
    if len(overlap) < 8:
        overlap = observed.index.intersection(model.index)
        overlap = overlap[overlap <= cutoff]
    if len(overlap) < 3:
        raise ValueError(f"Insufficient calibration overlap for {indicator.key}")
    anchor_year = int(overlap.max())
    unconstrained = float(observed.loc[anchor_year]) / float(model.loc[anchor_year])
    lower, upper = SCALE_BOUNDS[indicator.key]
    return float(np.clip(unconstrained, lower, upper)), overlap


def score_candidate(
    candidate: Candidate, indicators: list[Indicator], cutoff: int
) -> tuple[float, float, dict[str, float], dict[str, float]]:
    errors: dict[str, float] = {}
    scales: dict[str, float] = {}
    for indicator in indicators:
        model = candidate.simulation[indicator.key]
        scale, overlap = observation_mapping(indicator, model, cutoff)
        observed = indicator.observed.loc[overlap].to_numpy(dtype=float)
        predicted = scale * model.loc[overlap].to_numpy(dtype=float)
        errors[indicator.key] = float(np.sqrt(np.mean(np.square(np.log(predicted / observed)))))
        scales[indicator.key] = scale
    data_score = float(np.sqrt(np.mean(np.square(list(errors.values())))))
    prior_z = []
    for spec, value in zip(PARAMETERS, candidate.values):
        half_range = (spec.upper - spec.lower) / 2.0
        prior_z.append((float(value) - spec.baseline) / half_range)
    regularization = 0.0015 * float(np.mean(np.square(prior_z)))
    return data_score + regularization, data_score, scales, errors


def validation_error(
    candidate: Candidate,
    indicators: list[Indicator],
    segments: tuple[tuple[int, int], ...] = VALIDATION_SEGMENTS,
) -> tuple[float, dict[str, float]]:
    """Rolling-origin forecast error with an exact level anchor at each origin."""
    by_indicator: dict[str, list[float]] = {indicator.key: [] for indicator in indicators}
    for origin, evaluation_end in segments:
        for indicator in indicators:
            observed = indicator.observed.loc[
                (indicator.observed.index > origin)
                & (indicator.observed.index <= evaluation_end)
            ].dropna()
            if observed.empty:
                continue
            scale, _ = observation_mapping(indicator, candidate.simulation[indicator.key], origin)
            predicted = scale * candidate.simulation[indicator.key].reindex(observed.index)
            error = float(
                np.sqrt(
                    np.mean(
                        np.square(
                            np.log(
                                predicted.to_numpy(dtype=float)
                                / observed.to_numpy(dtype=float)
                            )
                        )
                    )
                )
            )
            by_indicator[indicator.key].append(error)
    summarized = {
        key: float(np.mean(values)) if values else float("nan")
        for key, values in by_indicator.items()
    }
    finite = [value for value in summarized.values() if np.isfinite(value)]
    return float(np.sqrt(np.mean(np.square(finite)))), summarized


def select_candidates(
    candidates: list[Candidate],
    indicators: list[Indicator],
    cutoff: int,
    segments: tuple[tuple[int, int], ...] = VALIDATION_SEGMENTS,
) -> pd.DataFrame:
    records = []
    for candidate in candidates:
        _, data_score, scales, errors = score_candidate(candidate, indicators, cutoff)
        forecast_score, forecast_errors = validation_error(candidate, indicators, segments)
        prior_z = []
        for spec, value in zip(PARAMETERS, candidate.values):
            half_range = (spec.upper - spec.lower) / 2.0
            prior_z.append((float(value) - spec.baseline) / half_range)
        finite_forecast_errors = [
            value for value in forecast_errors.values() if np.isfinite(value)
        ]
        worst_sector = max(finite_forecast_errors)
        boundary_count = sum(
            np.isclose(scales[key], SCALE_BOUNDS[key][0])
            or np.isclose(scales[key], SCALE_BOUNDS[key][1])
            for key in scales
        )
        objective = (
            forecast_score
            + 0.35 * worst_sector
            + 0.20 * data_score
            + 0.0005 * float(np.mean(np.square(prior_z)))
            + 0.01 * boundary_count
        )
        records.append(
            {
                "candidate_id": candidate.candidate_id,
                "objective": objective,
                "joint_log_rmse": data_score,
                "rolling_forecast_log_rmse": forecast_score,
                "worst_sector_forecast_log_rmse": worst_sector,
                "mapping_boundary_count": boundary_count,
                "scales": scales,
                "indicator_errors": errors,
                "forecast_indicator_errors": forecast_errors,
                "parameters": candidate.parameters(),
            }
        )
    return pd.DataFrame(records).sort_values(["objective", "candidate_id"]).reset_index(drop=True)


def mape(observed: pd.Series, predicted: pd.Series) -> float:
    overlap = observed.index.intersection(predicted.index)
    if len(overlap) == 0:
        return float("nan")
    return float(
        100.0
        * np.mean(
            np.abs(
                (predicted.loc[overlap].to_numpy(dtype=float) - observed.loc[overlap].to_numpy(dtype=float))
                / observed.loc[overlap].to_numpy(dtype=float)
            )
        )
    )


def evaluate_origin(
    candidates: list[Candidate],
    indicators: list[Indicator],
    origin: int,
    prediction_candidates: list[Candidate] | None = None,
) -> list[dict[str, float | int | str]]:
    available_segments = tuple(segment for segment in VALIDATION_SEGMENTS if segment[1] <= origin)
    if available_segments:
        ranking = select_candidates(candidates, indicators, origin, available_segments)
        admissible = ranking.loc[ranking["mapping_boundary_count"].eq(0)]
        selected_id = int((admissible if not admissible.empty else ranking).iloc[0]["candidate_id"])
    else:
        selected_id = 0
    selected = candidates[selected_id]
    prediction_selected = (
        selected if prediction_candidates is None else prediction_candidates[selected_id]
    )
    _, _, scales, _ = score_candidate(prediction_selected, indicators, origin)
    rows = []
    for indicator in indicators:
        observed = indicator.observed.loc[indicator.observed.index > origin].dropna()
        if observed.empty:
            continue
        prediction = scales[indicator.key] * prediction_selected.simulation[indicator.key]
        prediction = prediction.reindex(observed.index)
        reference = indicator.model.reindex(observed.index)
        if origin in indicator.observed.index and origin in indicator.model.index:
            anchor = float(indicator.observed.loc[origin]) / float(indicator.model.loc[origin])
        else:
            historical_scale, _ = observation_mapping(indicator, indicator.model, origin)
            anchor = historical_scale
        reference = reference * anchor
        rows.append(
            {
                "key": indicator.key,
                "cutoff": origin,
                "test_start": int(observed.index.min()),
                "test_end": int(observed.index.max()),
                "n": int(len(observed)),
                "bau2_level_anchored_mape_pct": mape(observed, reference),
                "bau2_e2026_mape_pct": mape(observed, prediction),
                "candidate_id": selected_id,
            }
        )
    return rows


def build_backtests(
    candidates: list[Candidate],
    indicators: list[Indicator],
    prediction_candidates: list[Candidate] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_origin = {
        origin: evaluate_origin(candidates, indicators, origin, prediction_candidates)
        for origin in (2005, 2010, 2015, 2018)
    }
    recent = pd.DataFrame(by_origin[2018])
    recent["improvement_pct"] = 100.0 * (
        recent["bau2_level_anchored_mape_pct"] - recent["bau2_e2026_mape_pct"]
    ) / recent["bau2_level_anchored_mape_pct"]

    multi_rows = []
    for indicator in indicators:
        rows = [row for origin in by_origin.values() for row in origin if row["key"] == indicator.key]
        total_n = sum(int(row["n"]) for row in rows)
        hybrid = sum(float(row["bau2_e2026_mape_pct"]) * int(row["n"]) for row in rows) / total_n
        reference = sum(float(row["bau2_level_anchored_mape_pct"]) * int(row["n"]) for row in rows) / total_n
        multi_rows.append(
            {
                "key": indicator.key,
                "origins": "/".join(str(row["cutoff"]) for row in rows),
                "n_origins": len(rows),
                "n": total_n,
                "bau2_level_anchored_mape_pct": reference,
                "bau2_e2026_mape_pct": hybrid,
                "improvement_pct": 100.0 * (reference - hybrid) / reference,
                "selection_rule": "joint candidate selected using observations ending at each origin",
            }
        )
    return recent, pd.DataFrame(multi_rows)


def structural_envelope(
    ensemble: list[Candidate], key: str, years: np.ndarray, scales: dict[int, float] | None = None
) -> tuple[np.ndarray, np.ndarray]:
    draws = []
    for candidate in ensemble:
        scale = 1.0 if scales is None else scales[candidate.candidate_id]
        draws.append(scale * candidate.simulation[key].reindex(years).to_numpy(dtype=float))
    values = np.vstack(draws)
    return np.quantile(values, 0.10, axis=0), np.quantile(values, 0.90, axis=0)


def plausibility_violations(
    candidate: Candidate,
    indicators: list[Indicator],
    scales: dict[str, float],
) -> list[str]:
    """Return transparent near-term guardrail failures for a production run.

    These are deliberately broad scenario guardrails, not fitted observations
    and not probability statements.  They keep the sensitivity band from being
    dominated by abrupt 2025--2035 collapses unsupported by current observations.
    """
    by_key = {indicator.key: indicator for indicator in indicators}
    violations: list[str] = []
    population = scales["population"] * candidate.simulation["population"]
    benchmark = by_key["population"].benchmark
    if benchmark is not None:
        for year, lower, upper in ((2030, 0.97, 1.03), (2035, 0.95, 1.05)):
            reference = float(benchmark.loc[year])
            value = float(population.loc[year])
            if not lower * reference <= value <= upper * reference:
                violations.append(f"population_{year}_outside_UN_guardrail")

    relative_floors = (
        ("food_per_capita", 2030, 0.75),
        ("food_per_capita", 2035, 0.55),
        ("industry_per_capita", 2030, 0.75),
        ("human_welfare", 2030, 0.85),
        ("human_welfare", 2035, 0.70),
    )
    for key, year, fraction in relative_floors:
        observed = by_key[key].observed.dropna()
        latest_value = float(observed.iloc[-1])
        projected = float(scales[key] * candidate.simulation[key].loc[year])
        if projected < fraction * latest_value:
            violations.append(f"{key}_{year}_below_{fraction:.2f}_of_latest")
    return violations


def add_plausibility_columns(
    ranking: pd.DataFrame,
    candidates: list[Candidate],
    indicators: list[Indicator],
) -> pd.DataFrame:
    annotated = ranking.copy()
    violations = []
    for _, row in annotated.iterrows():
        candidate = candidates[int(row["candidate_id"])]
        failures = plausibility_violations(candidate, indicators, row["scales"])
        violations.append(failures)
    annotated["plausibility_violation_count"] = [len(value) for value in violations]
    annotated["plausibility_violations"] = [";".join(value) for value in violations]
    return annotated


def select_medoid(
    ensemble: list[Candidate],
    indicators: list[Indicator],
    scales: dict[str, dict[int, float]],
) -> tuple[int, dict[int, float]]:
    """Choose one real coupled run nearest the ensemble's trajectory median."""
    years = np.arange(2025, 2051)
    vectors = []
    for candidate in ensemble:
        parts = []
        for indicator in indicators:
            values = (
                scales[indicator.key][candidate.candidate_id]
                * candidate.simulation[indicator.key].reindex(years).to_numpy(dtype=float)
            )
            parts.append(np.log(values))
        vectors.append(np.concatenate(parts))
    matrix = np.vstack(vectors)
    target = np.median(matrix, axis=0)
    distances = np.sqrt(np.mean(np.square(matrix - target), axis=1))
    by_id = {
        candidate.candidate_id: float(distance)
        for candidate, distance in zip(ensemble, distances)
    }
    selected = min(ensemble, key=lambda candidate: (by_id[candidate.candidate_id], candidate.candidate_id))
    return selected.candidate_id, by_id


def output_frame(
    years: np.ndarray,
    observed: pd.Series,
    original_bau: pd.Series,
    original_bau2: pd.Series,
    central: pd.Series,
    low: np.ndarray,
    high: np.ndarray,
    cutoff: int,
    benchmark: pd.Series | None = None,
) -> pd.DataFrame:
    central_values = central.reindex(years).to_numpy(dtype=float)
    frame = pd.DataFrame({"year": years})
    frame["observed"] = observed.reindex(years).to_numpy(dtype=float)
    frame["original_bau2"] = original_bau2.reindex(years).interpolate().to_numpy(dtype=float)
    frame["fitted"] = np.where(years <= cutoff, central_values, np.nan)
    frame["original_bau"] = original_bau.reindex(years).interpolate().to_numpy(dtype=float)
    frame["forecast_median"] = np.where(years >= cutoff, central_values, np.nan)
    # Preserve the actual ensemble quantiles.  The central line is one real
    # coupled World3 run (the medoid of observed targets), so it may legitimately
    # sit outside P10--P90 for a latent diagnostic that did not define the medoid.
    frame["p10"] = np.where(years >= cutoff, low, np.nan)
    frame["p90"] = np.where(years >= cutoff, high, np.nan)
    frame["alternate_bau"] = np.nan
    frame["sensitivity_low"] = frame["p10"]
    frame["sensitivity_high"] = frame["p90"]
    frame["benchmark"] = (
        benchmark.reindex(years).to_numpy(dtype=float) if benchmark is not None else np.nan
    )
    frame["hybrid_2026"] = central_values
    return frame


def export_identifiability(ranking: pd.DataFrame, ensemble_ids: list[int]) -> list[str]:
    accepted = ranking.loc[ranking["candidate_id"].isin(ensemble_ids)]
    rows = []
    weak = []
    for spec in PARAMETERS:
        values = np.array([record[spec.key] for record in accepted["parameters"]], dtype=float)
        prior_width = spec.upper - spec.lower
        retained_fraction = float((values.max() - values.min()) / prior_width)
        if retained_fraction >= 0.50:
            weak.append(spec.key)
        rows.append(
            {
                "parameter": spec.key,
                "model_name": spec.model_name,
                "prior_lower": spec.lower,
                "prior_upper": spec.upper,
                "accepted_min": float(values.min()),
                "accepted_median": float(np.median(values)),
                "accepted_max": float(values.max()),
                "accepted_range_fraction_of_prior": retained_fraction,
                "weakly_identified": retained_fraction >= 0.50,
            }
        )
    pd.DataFrame(rows).to_csv(OUTPUT / "parameter_identifiability.csv", index=False)
    return weak


def export_fit_diagnostics(indicators: list[Indicator], central_series: dict[str, pd.Series]) -> None:
    rows = []
    for indicator in indicators:
        observed = indicator.observed.dropna()
        predicted = central_series[indicator.key].reindex(observed.index)
        valid = predicted.notna()
        observed = observed.loc[valid]
        predicted = predicted.loc[valid]
        errors = predicted.to_numpy(dtype=float) / observed.to_numpy(dtype=float) - 1.0
        rows.append(
            {
                "key": indicator.key,
                "obs_start": int(observed.index.min()),
                "obs_end": int(observed.index.max()),
                "n": int(len(observed)),
                "historical_mape_pct": float(100.0 * np.mean(np.abs(errors))),
                "historical_bias_pct": float(100.0 * np.mean(errors)),
            }
        )
    pd.DataFrame(rows).to_csv(OUTPUT / "fit_diagnostics.csv", index=False)


def export_bridge_validation(
    candidates: list[Candidate], indicators: list[Indicator]
) -> None:
    """Document bridge selection using only information through 2018."""
    rows = []
    for sector in ("food_per_capita", "pollution_pressure"):
        sector_rows = []
        for weight in BRIDGE_WEIGHT_GRID:
            bridged = apply_observation_bridges(
                candidates,
                food_world3_weight=(weight if sector == "food_per_capita" else 1.0),
                pollution_world3_weight=(weight if sector == "pollution_pressure" else 1.0),
            )
            ranking = select_candidates(bridged, indicators, SELECTION_CUTOFF)
            eligible = ranking.loc[ranking["mapping_boundary_count"].eq(0)]
            selected = (eligible if not eligible.empty else ranking).iloc[0]
            sector_rows.append(
                {
                    "sector": sector,
                    "world3_signal_weight": weight,
                    "industrial_capacity_weight": 1.0 - weight,
                    "pre2019_objective": float(selected["objective"]),
                    "pre2019_sector_log_rmse": float(
                        selected["forecast_indicator_errors"][sector]
                    ),
                    "selected_candidate_id": int(selected["candidate_id"]),
                }
            )
        chosen = min(
            sector_rows,
            key=lambda row: (row["pre2019_objective"], -row["world3_signal_weight"]),
        )
        expected = (
            FOOD_WORLD3_WEIGHT
            if sector == "food_per_capita"
            else POLLUTION_WORLD3_WEIGHT
        )
        if not np.isclose(chosen["world3_signal_weight"], expected):
            raise RuntimeError(
                f"Pre-2019 bridge audit selected {chosen['world3_signal_weight']} "
                f"for {sector}, not the declared {expected}"
            )
        for row in sector_rows:
            row["chosen"] = bool(
                np.isclose(row["world3_signal_weight"], expected)
            )
            rows.append(row)
    pd.DataFrame(rows).to_csv(OUTPUT / "bridge_validation.csv", index=False)


def export_outputs(candidates: list[Candidate], indicators: list[Indicator]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    export_bridge_validation(candidates, indicators)
    bridged_candidates = apply_observation_bridges(candidates)
    # First select a validation model with the structure frozen at 2018.  It is
    # used only for the reported holdout/backtests.  After that evidence is
    # preserved, a separate production refit may use all current observations.
    validation_ranking = select_candidates(candidates, indicators, SELECTION_CUTOFF)
    validation_eligible = validation_ranking.loc[
        validation_ranking["mapping_boundary_count"].eq(0)
    ]
    if validation_eligible.empty:
        validation_eligible = validation_ranking
    validation_id = int(validation_eligible.iloc[0]["candidate_id"])
    validation_candidate = candidates[validation_id]

    latest_cutoff = max(int(indicator.observed.index.max()) for indicator in indicators)
    production_ranking = select_candidates(
        candidates, indicators, latest_cutoff, PRODUCTION_SEGMENTS
    )
    production_ranking = add_plausibility_columns(
        production_ranking, candidates, indicators
    )
    production_eligible = production_ranking.loc[
        production_ranking["mapping_boundary_count"].eq(0)
        & production_ranking["plausibility_violation_count"].eq(0)
    ]
    if len(production_eligible) < ENSEMBLE_SIZE:
        raise RuntimeError(
            f"Fewer than {ENSEMBLE_SIZE} candidates satisfy both mapping and plausibility guardrails; "
            "increase the predeclared candidate design instead of silently relaxing them"
        )
    ensemble_ids = [
        int(value) for value in production_eligible.head(ENSEMBLE_SIZE)["candidate_id"]
    ]
    ensemble = [candidates[value] for value in ensemble_ids]
    raw_ensemble_scales: dict[str, dict[int, float]] = {indicator.key: {} for indicator in indicators}
    for candidate in ensemble:
        _, _, scales, _ = score_candidate(candidate, indicators, latest_cutoff)
        for key, scale in scales.items():
            raw_ensemble_scales[key][candidate.candidate_id] = scale
    central_id, medoid_distances = select_medoid(ensemble, indicators, raw_ensemble_scales)
    central = candidates[central_id]
    bridged_central = bridged_candidates[central_id]
    central_rank = production_ranking.loc[
        production_ranking["candidate_id"].eq(central_id)
    ].iloc[0]
    _, _, structural_scales, structural_errors = score_candidate(
        central, indicators, latest_cutoff
    )
    _, _, central_scales, central_errors = score_candidate(
        bridged_central, indicators, latest_cutoff
    )

    bridged_ensemble = [bridged_candidates[value] for value in ensemble_ids]
    ensemble_scales: dict[str, dict[int, float]] = {indicator.key: {} for indicator in indicators}
    for candidate in bridged_ensemble:
        _, _, scales, _ = score_candidate(candidate, indicators, latest_cutoff)
        for key, scale in scales.items():
            ensemble_scales[key][candidate.candidate_id] = scale

    exported_central: dict[str, pd.Series] = {}
    for indicator in indicators:
        years = np.arange(1950, 2101)
        central_series = central_scales[indicator.key] * bridged_central.simulation[indicator.key].reindex(years)
        low, high = structural_envelope(
            bridged_ensemble, indicator.key, years, ensemble_scales[indicator.key]
        )
        last_observed = int(indicator.observed.index.max())
        frame = output_frame(
            years, indicator.observed, indicator.model_alt, indicator.model,
            central_series, low, high, last_observed, indicator.benchmark
        )
        frame.to_csv(OUTPUT / f"{indicator.key}.csv", index=False, float_format="%.8g")
        exported_central[indicator.key] = central_series

    empirical = pd.read_csv(ROOT / "data" / "processed" / "empirical_model_inputs_2026-08-28.csv").set_index("year")
    bau = pd.read_csv(ROOT / "outputs" / "world3_03_bau.csv").set_index("year")
    bau2 = pd.read_csv(ROOT / "outputs" / "world3_03_bau2.csv").set_index("year")
    bau.index = bau.index.astype(int)
    bau2.index = bau2.index.astype(int)
    years = np.arange(1950, 2101)

    industry_observed = 100.0 * empirical["industrial_output"].dropna() / float(empirical.loc[2015, "industrial_output"])
    industry_anchor_year = int(industry_observed.index.max())
    industry_anchor_value = float(industry_observed.loc[industry_anchor_year])
    industry_central = (
        central.simulation["industry_total"]
        * industry_anchor_value
        / float(central.simulation["industry_total"].loc[industry_anchor_year])
    )
    industry_ensemble_scales = {
        candidate.candidate_id: industry_anchor_value
        / float(candidate.simulation["industry_total"].loc[industry_anchor_year])
        for candidate in ensemble
    }
    common_resource_base = 1.0e12
    resource_central = (
        central.simulation["resources_remaining_pct"]
        * float(central.values[0])
        / common_resource_base
    )
    resource_ensemble_scales = {
        candidate.candidate_id: float(candidate.values[0]) / common_resource_base
        for candidate in ensemble
    }
    diagnostic_specs = (
        (
            "industry_total", industry_observed,
            100.0 * bau["industrial_output"] / float(bau.loc[2015, "industrial_output"]),
            100.0 * bau2["industrial_output"] / float(bau2.loc[2015, "industrial_output"]),
            industry_anchor_year, industry_central, industry_ensemble_scales,
        ),
        (
            "persistent_pollution_stock", pd.Series(dtype=float),
            100.0 * bau["persistent_pollution"] / float(bau.loc[1990, "persistent_pollution"]),
            100.0 * bau2["persistent_pollution"] / float(bau2.loc[1990, "persistent_pollution"]),
            2025, central.simulation["persistent_pollution_stock"], None,
        ),
        (
            "resources_remaining_pct", pd.Series(dtype=float),
            100.0 * bau["nonrenewable_resources"] / common_resource_base,
            100.0 * bau2["nonrenewable_resources"] / common_resource_base,
            2025, resource_central, resource_ensemble_scales,
        ),
    )
    for key, observed, original_bau, original_bau2, cutoff, central_source, diagnostic_scales in diagnostic_specs:
        central_series = central_source.reindex(years)
        low, high = structural_envelope(ensemble, key, years, diagnostic_scales)
        frame = output_frame(
            years, observed, original_bau, original_bau2,
            central_series, low, high, cutoff
        )
        frame.to_csv(OUTPUT / f"{key}.csv", index=False, float_format="%.8g")

    recent, multi = build_backtests(candidates, indicators, bridged_candidates)
    recent.to_csv(OUTPUT / "backtest_2019_latest.csv", index=False)
    multi.to_csv(OUTPUT / "backtest_multi_origin.csv", index=False)

    production_export = production_ranking.drop(
        columns=["scales", "indicator_errors", "forecast_indicator_errors", "parameters"]
    ).copy()
    production_export.to_csv(OUTPUT / "candidate_ranking.csv", index=False)
    validation_export = validation_ranking.drop(
        columns=["scales", "indicator_errors", "forecast_indicator_errors", "parameters"]
    ).copy()
    validation_export.to_csv(OUTPUT / "validation_candidate_ranking.csv", index=False)
    weak_parameters = export_identifiability(production_ranking, ensemble_ids)
    export_fit_diagnostics(indicators, exported_central)
    manifest = {
        "model": "BAU Hybrid 2026 Joint",
        "version": "0.10.0",
        "scientific_status": "experimental scenario model; not a probabilistic forecast",
        "generated_on": SNAPSHOT_DATE,
        "structural_model": "official World3-03 scenario 2 (BAU2)",
        "method": "locked structural validation model selected through 2018, followed by a separate production refit using all available observations; the displayed medoid remains one common World3-03 parameter vector; food and annual CO2 use fixed empirical observation bridges selected only with pre-2019 data and do not alter structural selection or feedbacks",
        "candidate_count": len(candidates),
        "selection_cutoff": SELECTION_CUTOFF,
        "production_fit_cutoff": latest_cutoff,
        "validation_candidate_id": validation_id,
        "validation_parameters": validation_candidate.parameters(),
        "central_candidate_id": central_id,
        "production_candidate_id": central_id,
        "ensemble_candidate_ids": ensemble_ids,
        "central_selection_rule": f"trajectory medoid of the {len(ensemble_ids)} best production candidates satisfying all mapping and near-term plausibility guardrails",
        "central_medoid_log_rms_distance": medoid_distances[central_id],
        "joint_log_rmse": float(central_rank["joint_log_rmse"]),
        "rolling_forecast_log_rmse": float(central_rank["rolling_forecast_log_rmse"]),
        "central_mapping_boundary_count_at_selection": int(central_rank["mapping_boundary_count"]),
        "central_plausibility_violation_count": int(central_rank["plausibility_violation_count"]),
        "central_parameters": central.parameters(),
        "parameter_bounds": {
            spec.key: {"model_name": spec.model_name, "baseline": spec.baseline, "lower": spec.lower, "upper": spec.upper}
            for spec in PARAMETERS
        },
        "weakly_identified_parameters": weak_parameters,
        "observation_scales": central_scales,
        "structural_observation_scales": structural_scales,
        "observation_scale_bounds": SCALE_BOUNDS,
        "indicator_log_rmse": central_errors,
        "structural_indicator_log_rmse": structural_errors,
        "observation_bridges": {
            "selection_cutoff": SELECTION_CUTOFF,
            "food_per_capita": {
                "world3_food_weight": FOOD_WORLD3_WEIGHT,
                "industrial_input_capacity_weight": 1.0 - FOOD_WORLD3_WEIGHT,
                "form": "geometric Cobb-Douglas-like observation operator",
                "selection": "five predeclared weights evaluated with data and rolling validation ending no later than 2018",
            },
            "pollution_pressure": {
                "world3_persistent_pollution_generation_weight": POLLUTION_WORLD3_WEIGHT,
                "industrial_throughput_weight": 1.0 - POLLUTION_WORLD3_WEIGHT,
                "form": "annual CO2 activity proxy; persistent pollution stock remains a separate latent World3 diagnostic",
                "selection": "five predeclared weights evaluated with data and rolling validation ending no later than 2018",
            },
        },
        "uncertainty": (
            f"10th--90th percentile across {len(ensemble_ids)} best production candidates "
            "with admissible observation mappings and transparent near-term guardrails; sensitivity envelope, not a calibrated probability interval"
        ),
        "band_definition": "actual pointwise 10th and 90th percentiles of the accepted ensemble; the displayed medoid is not forced inside the band and may fall outside it for latent diagnostics",
        "plausibility_guardrails": {
            "population": "2030 within +/-3% and 2035 within +/-5% of UN WPP 2024 medium",
            "food_per_capita": "2030 at least 75% and 2035 at least 55% of latest observation",
            "industry_per_capita": "2030 at least 75% of latest observation",
            "human_welfare": "2030 at least 85% and 2035 at least 70% of latest observation",
            "interpretation": "broad scenario admissibility constraints, not fitted observations or probability bounds",
        },
        "validation": "the reported 2019-latest holdout belongs only to the model-selection procedure frozen in 2018; the displayed production trajectory is a separate post-validation refit using all available observations and is not itself a holdout forecast",
        "food_mapping": "FAOSTAT food per capita is mapped to 25% World3 food signal and 75% industrial-input-capacity signal in log space; this observation bridge does not feed back into World3",
        "pollution_mapping": "annual CO2 uses industrial throughput as an activity proxy; World3 persistent pollution generation and stock remain latent and continue to drive the model feedbacks",
        "diagnostics": "total industrial output is level-anchored at its 2025 observation but excluded from fitting because it is algebraically redundant with population and per-capita output; persistent pollution stock and remaining resources are latent World3 states without direct observations; all resource curves use the common BAU-1900 stock denominator of 1e12 units",
        "important_limit": "the food and CO2 bridges improve observed-output validation but are not new feedback states; HDI remains a proxy; EROI, climate-water, minerals and AI are not yet coupled into the central run",
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)


def main() -> None:
    indicators, _ = build_indicators()
    values = parameter_candidates()
    candidates = run_candidates(values)
    export_outputs(candidates, indicators)
    print(f"Saved joint BAU Hybrid 2026 datasets to {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
