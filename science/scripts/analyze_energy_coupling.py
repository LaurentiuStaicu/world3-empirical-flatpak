"""Audit a conservative EROI feedback against BAU Hybrid 2026 v0.10.0.

This script does not replace the production trajectory.  It tests whether an
energy-quality feedback can be introduced without a discontinuity, without
double counting the resource-capital burden already present in World3, and
with interpretable scenario ordering.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import warnings

import numpy as np
import pandas as pd
import pysd

from build_joint_hybrid_2026 import (
    MODEL_COLUMNS,
    YEARS,
    model_parameters,
    parameter_candidates,
    transform_outputs,
)
from world3_empirical.energy_coupling import EROI_SCENARIOS, coupled_model_text
from world3_empirical.world3_03 import _sanitized_model_text, _source_model_path


ROOT = Path(__file__).resolve().parents[1]
HYBRID_OUTPUT = ROOT / "outputs" / "joint_hybrid_2026"
OUTPUT = ROOT / "outputs" / "energy_coupling"
ENERGY_COLUMNS = [
    "energy system eroi",
    "energy system reinvestment share",
    "energy capital burden",
    "world3 fraction of industrial capital allocated to obtaining resources",
    "fraction of industrial capital allocated to obtaining resources",
]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    hybrid_manifest = json.loads((HYBRID_OUTPUT / "manifest.json").read_text())
    central_id = int(hybrid_manifest["central_candidate_id"])
    values = parameter_candidates()[central_id]

    cached = np.load(HYBRID_OUTPUT / "candidate_simulations.npz")
    resource_reference = float(
        cached["series_resources_remaining_pct"][central_id, int(2025 - YEARS[0])] / 100.0
    )

    with tempfile.TemporaryDirectory(prefix="world3_eroi_audit_") as directory:
        model_path = Path(directory) / "World3_03_Energy_Coupled.mdl"
        model_path.write_text(
            coupled_model_text(_sanitized_model_text(_source_model_path())),
            encoding="utf-8",
        )
        model = pysd.read_vensim(model_path)
        frames: dict[str, pd.DataFrame] = {}
        transformed: dict[str, dict[str, pd.Series]] = {}
        effective_scenarios = {}
        warning_records = []
        for name, scenario in EROI_SCENARIOS.items():
            scenario = type(scenario)(
                **{
                    **vars(scenario),
                    "resource_fraction_reference": resource_reference,
                }
            )
            effective_scenarios[name] = scenario
            params = model_parameters(values) | scenario.model_parameters()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                frame = model.run(
                    params=params,
                    return_columns=MODEL_COLUMNS + ENERGY_COLUMNS,
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
            messages = [str(item.message) for item in lookup_warnings]
            warning_records.append(
                {
                    "scenario": name,
                    "total": len(messages),
                    "above": sum("above the maximum" in value for value in messages),
                    "below": sum("below the minimum" in value for value in messages),
                    "unique": len(set(messages)),
                }
            )
            frame.index = frame.index.astype(int)
            frames[name] = frame
            transformed[name] = transform_outputs(frame[MODEL_COLUMNS])

    pd.DataFrame(warning_records).to_csv(
        OUTPUT / "lookup_extrapolation_audit.csv", index=False
    )

    uncoupled = frames["uncoupled"]
    records: list[dict[str, float | str | int]] = []
    for name, frame in frames.items():
        for year in (2025, 2030, 2035, 2050, 2100):
            row: dict[str, float | str | int] = {
                "scenario": name,
                "year": year,
                "system_eroi": float(frame.loc[year, "energy system eroi"]),
                "energy_reinvestment_pct": 100.0
                * float(frame.loc[year, "energy system reinvestment share"]),
                "energy_capital_burden_pct": 100.0
                * float(frame.loc[year, "energy capital burden"]),
                "world3_resource_capital_burden_pct": 100.0
                * float(
                    frame.loc[
                        year,
                        "world3 fraction of industrial capital allocated to obtaining resources",
                    ]
                ),
                "effective_resource_capital_burden_pct": 100.0
                * float(
                    frame.loc[
                        year,
                        "fraction of industrial capital allocated to obtaining resources",
                    ]
                ),
            }
            for key in (
                "population",
                "industry_per_capita",
                "food_per_capita",
                "pollution_pressure",
                "human_welfare",
            ):
                value = float(transformed[name][key].loc[year])
                reference = float(transformed["uncoupled"][key].loc[year])
                row[key] = value
                row[f"{key}_change_pct"] = 100.0 * (value / reference - 1.0)
            records.append(row)

    summary = pd.DataFrame.from_records(records)
    summary.to_csv(OUTPUT / "scenario_summary.csv", index=False, float_format="%.8g")

    full = []
    for name, frame in frames.items():
        selected = frame[ENERGY_COLUMNS].copy()
        selected.insert(0, "scenario", name)
        selected.insert(1, "year", selected.index.astype(int))
        for key in (
            "population",
            "industry_per_capita",
            "food_per_capita",
            "pollution_pressure",
            "human_welfare",
        ):
            selected[key] = transformed[name][key].to_numpy(dtype=float)
        full.append(selected.reset_index(drop=True))
    pd.concat(full, ignore_index=True).to_csv(
        OUTPUT / "scenario_timeseries.csv", index=False, float_format="%.8g"
    )

    pre_boundary_columns = MODEL_COLUMNS
    central_difference = np.max(
        np.abs(
            frames["conservative_central"].loc[:2025, pre_boundary_columns].to_numpy()
            - uncoupled.loc[:2025, pre_boundary_columns].to_numpy()
        )
    )
    uncoupled_difference = max(
        float(
            np.max(
                np.abs(
                    transformed["uncoupled"][key].to_numpy(dtype=float)
                    - cached[f"series_{key}"][central_id].astype(float)
                )
            )
        )
        for key in (
            "population",
            "industry_per_capita",
            "food_per_capita",
            "pollution_pressure",
            "human_welfare",
            "industry_total",
            "persistent_pollution_stock",
            "resources_remaining_pct",
        )
    )
    audit = {
        "module": "conservative_eroi_world3_coupling",
        "version": "0.11.0-development-audit",
        "status": "structural_sensitivity_not_empirically_calibrated",
        "production_decision": "not_accepted_into_central_projection",
        "central_candidate_id": central_id,
        "resource_fraction_reference_2025": resource_reference,
        "observed_fossil_share_2025": EROI_SCENARIOS[
            "conservative_central"
        ].fossil_share_initial,
        "energy_data_snapshot": "data/processed/energy_institute_global_2026.csv",
        "eroi_observation_snapshot": (
            "data/processed/aramendia_global_fossil_eroi_2024.csv"
        ),
        "eroi_article_doi": "10.1038/s41560-024-01518-6",
        "eroi_dataset_doi": "10.6084/m9.figshare.25311358",
        "eroi_accounting_boundary": "final-stage EROI, indirect energy included",
        "fossil_eroi_anchor_year": 2020,
        "fossil_eroi_anchor_value": EROI_SCENARIOS[
            "conservative_central"
        ].fossil_eroi_initial,
        "anchor_extrapolation_to_2025": (
            "persistence; it had the lowest five-year multi-origin RMSE at the "
            "final-stage boundary"
        ),
        "resource_link_backtest": (
            "outputs/energy_coupling/eroi_resource_link_summary.csv"
        ),
        "resource_link_accepted": False,
        "pre2025_coupled_vs_uncoupled_max_absolute_difference": float(central_difference),
        "uncoupled_patch_invariance_max_absolute_difference": float(uncoupled_difference),
        "double_counting_control": (
            "effective resource-capital burden is max(original World3 burden, "
            "EROI-derived burden), never their sum"
        ),
        "boundary_rule": "EROI-derived burden equals the World3 floor in 2025",
        "important_limit": (
            "A homogeneous global fossil EROI series is available for 1971-2020, but "
            "the proposed World3 resource-fraction link failed five-year multi-origin "
            "validation against persistence at primary, final and useful accounting "
            "boundaries. The coupling may inform structural sensitivity but cannot "
            "replace the v0.10.0 central run."
        ),
        "scenarios": {name: vars(value) for name, value in effective_scenarios.items()},
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(summary.to_string(index=False))
    print(json.dumps(audit, indent=2, ensure_ascii=False))
if __name__ == "__main__":
    main()
