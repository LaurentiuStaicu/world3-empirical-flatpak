#!/usr/bin/env python3
"""Dependency-free static validation for the Flatpak source project."""

import configparser
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


APP_ID = "io.github.laurentiustaicu.World3Empirical"
ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> None:
    ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml")
    ET.parse(ROOT / "data" / "icons" / f"{APP_ID}.svg")

    desktop = configparser.ConfigParser(interpolation=None)
    desktop.read(ROOT / "data" / f"{APP_ID}.desktop", encoding="utf-8")
    entry = desktop["Desktop Entry"]
    if entry.get("Exec") != APP_ID or entry.get("Icon") != APP_ID:
        fail("Desktop Exec/Icon must match the application id")

    manifest = (ROOT / f"{APP_ID}.yml").read_text(encoding="utf-8")
    for required in (
        f"app-id: {APP_ID}",
        "runtime: io.elementary.Platform",
        "runtime-version: '8'",
        "sdk: io.elementary.Sdk",
        "--socket=fallback-x11",
        "--socket=wayland",
    ):
        if required not in manifest:
            fail(f"Missing Flatpak manifest setting: {required}")

    meson = (ROOT / "meson.build").read_text(encoding="utf-8")
    if "find_library('m', required: true)" not in meson or "[gtk, granite, math]" not in meson:
        fail("Meson must link libm for Math.round")

    required_columns = {
        "year", "observed", "original_bau", "original_bau2", "hybrid_2026",
        "forecast_median", "p10", "p90", "benchmark",
    }
    calibrated = (
        "population.csv", "industry_per_capita.csv", "food_per_capita.csv",
        "pollution_pressure.csv", "human_welfare.csv",
    )
    diagnostics = (
        "industry_total.csv", "persistent_pollution_stock.csv",
        "resources_remaining_pct.csv",
    )
    indicators = calibrated + diagnostics
    calculated_diagnostics = {}
    for scenario in indicators:
        with (ROOT / "data" / "scenarios" / scenario).open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows or not required_columns.issubset(set(rows[0])):
            fail(f"{scenario} has an invalid schema")
        if int(rows[0]["year"]) != 1950 or int(rows[-1]["year"]) != 2100:
            fail(f"{scenario} must cover 1950–2100")
        has_observations = any(row["observed"] for row in rows)
        if scenario in calibrated and not has_observations:
            fail(f"{scenario} must contain empirical observations")
        if scenario in ("persistent_pollution_stock.csv", "resources_remaining_pct.csv") and has_observations:
            fail(f"{scenario} must remain explicitly latent")
        if not any(row["forecast_median"] for row in rows):
            fail(f"{scenario} must contain a forecast")
        if not all(row["original_bau"] and row["original_bau2"] for row in rows):
            fail(f"{scenario} must contain both original World3 trajectories")
        if not any(row["hybrid_2026"] for row in rows):
            fail(f"{scenario} must contain BAU Hybrid 2026")
        projected = [row for row in rows if row["forecast_median"]]
        for row in projected:
            p10 = float(row["p10"])
            p90 = float(row["p90"])
            if p10 > p90:
                fail(f"{scenario} has reversed structural quantiles")
        if scenario in calibrated:
            latest = [row for row in rows if row["observed"]][-1]
            if abs(float(latest["observed"]) - float(latest["hybrid_2026"])) > 1e-6:
                fail(f"{scenario} is not anchored at its latest observation")
            paired = [row for row in rows if row["observed"] and row["hybrid_2026"]]
            errors = [float(row["hybrid_2026"]) / float(row["observed"]) - 1 for row in paired]
            calculated_diagnostics[scenario.removesuffix(".csv")] = {
                "start": int(paired[0]["year"]),
                "end": int(paired[-1]["year"]),
                "n": len(paired),
                "mape": 100 * sum(abs(value) for value in errors) / len(errors),
                "bias": 100 * sum(errors) / len(errors),
            }

    model_manifest = json.loads(
        (ROOT / "data" / "scenarios" / "bau_hybrid_2026_manifest.json").read_text(encoding="utf-8")
    )
    if model_manifest.get("model") != "BAU Hybrid 2026 Joint":
        fail("Model manifest does not identify the joint BAU Hybrid 2026 model")
    if model_manifest.get("structural_model") != "official World3-03 scenario 2 (BAU2)":
        fail("Hybrid must use the official World3-03 BAU2 structure")
    if len(model_manifest.get("central_parameters", {})) != 7:
        fail("Hybrid must expose one common seven-parameter vector")
    if model_manifest.get("version") != "0.10.0":
        fail("Scientific manifest must be version 0.10.0")
    if model_manifest.get("candidate_count") != 128:
        fail("Scientific ensemble must contain 128 predeclared candidates")
    if model_manifest.get("selection_cutoff") != 2018:
        fail("Structural selection must be frozen before the recent holdout")
    if model_manifest.get("central_mapping_boundary_count_at_selection") != 0:
        fail("Central run must not require a mapping at its admissible boundary")
    if len(model_manifest.get("ensemble_candidate_ids", [])) < 12:
        fail("Structural sensitivity ensemble is too small")
    if model_manifest.get("production_fit_cutoff") != 2025:
        fail("Displayed production model must use observations through 2025")
    if model_manifest.get("validation_candidate_id") == model_manifest.get("production_candidate_id"):
        fail("Validation and production models must be explicitly separate")
    if model_manifest.get("central_plausibility_violation_count") != 0:
        fail("Central production run violates a declared plausibility guardrail")
    if model_manifest.get("central_candidate_id") not in model_manifest.get("ensemble_candidate_ids", []):
        fail("Central production run must be a real member of the ensemble")
    bridges = model_manifest.get("observation_bridges", {})
    if bridges.get("selection_cutoff") != 2018:
        fail("Observation bridges must be selected without post-2018 data")
    if bridges.get("food_per_capita", {}).get("world3_food_weight") != 0.25:
        fail("Food observation bridge must retain the validated 25% World3 weight")
    if bridges.get("pollution_pressure", {}).get(
        "world3_persistent_pollution_generation_weight"
    ) != 0.0:
        fail("Annual CO2 bridge must retain the validated activity-proxy mapping")
    if "do not alter structural selection" not in model_manifest.get("method", ""):
        fail("Manifest must distinguish observation bridges from World3 feedbacks")

    with (ROOT / "data" / "scenarios" / "bridge_validation.csv").open(
        encoding="utf-8"
    ) as handle:
        bridge_rows = list(csv.DictReader(handle))
    if len(bridge_rows) != 10:
        fail("Bridge validation must contain five predeclared weights per sector")
    chosen = {row["sector"]: row for row in bridge_rows if row["chosen"] == "True"}
    if set(chosen) != {"food_per_capita", "pollution_pressure"}:
        fail("Bridge validation must select exactly one weight per sector")

    with (ROOT / "data" / "scenarios" / "backtest_2019_latest.csv").open(
        encoding="utf-8"
    ) as handle:
        backtests = list(csv.DictReader(handle))
    expected_keys = [name.removesuffix(".csv") for name in calibrated]
    if [row["key"] for row in backtests] != expected_keys:
        fail("Backtest rows must match the indicator order")
    improved = sum(float(row["improvement_pct"]) > 0 for row in backtests)
    if improved != 5:
        fail("Joint hybrid must improve all five recent indicator holdouts")
    total_n = sum(int(row["n"]) for row in backtests)
    reference = sum(int(row["n"]) * float(row["bau2_level_anchored_mape_pct"]) for row in backtests) / total_n
    hybrid = sum(int(row["n"]) * float(row["bau2_e2026_mape_pct"]) for row in backtests) / total_n
    if hybrid >= reference:
        fail("Joint hybrid must improve the weighted recent holdout error")

    with (ROOT / "data" / "scenarios" / "backtest_multi_origin.csv").open(
        encoding="utf-8"
    ) as handle:
        multi_origin = list(csv.DictReader(handle))
    if [row["key"] for row in multi_origin] != expected_keys:
        fail("Multi-origin rows must match the indicator order")
    for row in multi_origin:
        if int(row["n_origins"]) < 3 or int(row["n"]) < 30:
            fail("Multi-origin validation has insufficient coverage")
        if "ending at each origin" not in row["selection_rule"]:
            fail("Multi-origin parameter selection may contain future leakage")
    multi_by_key = {row["key"]: row for row in multi_origin}
    for key in ("food_per_capita", "pollution_pressure"):
        if float(multi_by_key[key]["improvement_pct"]) <= 0:
            fail(f"{key} bridge must improve multi-origin validation")

    with (ROOT / "data" / "scenarios" / "fit_diagnostics.csv").open(
        encoding="utf-8"
    ) as handle:
        diagnostics = list(csv.DictReader(handle))
    if [row["key"] for row in diagnostics] != expected_keys:
        fail("Fit diagnostics must match the indicator order")
    for row in diagnostics:
        if int(row["n"]) < 30 or float(row["historical_mape_pct"]) <= 0:
            fail("Fit diagnostics have insufficient coverage")
        expected = calculated_diagnostics[row["key"]]
        if (
            int(row["obs_start"]) != expected["start"]
            or int(row["obs_end"]) != expected["end"]
            or int(row["n"]) != expected["n"]
            or abs(float(row["historical_mape_pct"]) - expected["mape"]) > 0.01
            or abs(float(row["historical_bias_pct"]) - expected["bias"]) > 0.01
        ):
            fail(f"Fit diagnostics disagree with {row['key']}.csv")

    with (ROOT / "data" / "scenarios" / "parameter_identifiability.csv").open(
        encoding="utf-8"
    ) as handle:
        identification = list(csv.DictReader(handle))
    if len(identification) != 7:
        fail("Identifiability report must cover all seven structural parameters")

    with (ROOT / "data" / "scenarios" / "candidate_ranking.csv").open(
        encoding="utf-8"
    ) as handle:
        production_ranking = {
            int(row["candidate_id"]): row for row in csv.DictReader(handle)
        }
    for candidate_id in model_manifest.get("ensemble_candidate_ids", []):
        row = production_ranking[candidate_id]
        if int(row["mapping_boundary_count"]) != 0:
            fail("A production ensemble member uses a boundary mapping")
        if int(row["plausibility_violation_count"]) != 0:
            fail("A production ensemble member violates a guardrail")

    validation_ranking = ROOT / "data" / "scenarios" / "validation_candidate_ranking.csv"
    if not validation_ranking.exists():
        fail("Frozen validation candidate ranking is missing")

    industry_rows = []
    with (ROOT / "data" / "scenarios" / "industry_total.csv").open(encoding="utf-8") as handle:
        industry_rows = [row for row in csv.DictReader(handle) if row["observed"]]
    latest_industry = industry_rows[-1]
    if abs(float(latest_industry["observed"]) - float(latest_industry["hybrid_2026"])) > 1e-6:
        fail("Total industrial output must be anchored at its latest observation")

    with (ROOT / "data" / "scenarios" / "resources_remaining_pct.csv").open(
        encoding="utf-8"
    ) as handle:
        resource_2030 = next(
            row for row in csv.DictReader(handle) if int(row["year"]) == 2030
        )
    if float(resource_2030["hybrid_2026"]) >= float(resource_2030["p10"]):
        fail("The latent-resource medoid appears to have been forced into P10-P90")

    ui_source = (ROOT / "src" / "MainWindow.vala").read_text(encoding="utf-8")
    for required_ui_text in (
        "Potrivire retrospectivă după MAPE",
        "sprijin empiric intern al proiecției",
        "projection_support_score",
        "nu susține o prognoză autonomă",
    ):
        if required_ui_text not in ui_source:
            fail(f"Projection-support disclosure is missing: {required_ui_text}")

    def error_points(value: float, high: float, medium: float, low: float) -> int:
        return 3 if value <= high else 2 if value <= medium else 1 if value <= low else 0

    expected_support = {}
    for index, key in enumerate(expected_keys):
        fit_value = float(diagnostics[index]["historical_mape_pct"])
        recent_value = float(backtests[index]["bau2_e2026_mape_pct"])
        multi_value = float(multi_origin[index]["bau2_e2026_mape_pct"])
        score = (
            error_points(fit_value, 5, 15, 30)
            + error_points(recent_value, 2, 5, 10)
            + error_points(multi_value, 3, 7, 15)
        )
        recent_better = recent_value <= float(backtests[index]["bau2_level_anchored_mape_pct"])
        multi_better = multi_value <= float(multi_origin[index]["bau2_level_anchored_mape_pct"])
        if not multi_better:
            score = min(score, 5)
        if not recent_better and not multi_better:
            score = min(score, 2)
        if key == "food_per_capita":
            score = min(score, 7)
        if key == "pollution_pressure":
            score = min(score, 4)
        expected_support[key] = score
    if expected_support != {
        "population": 5,
        "industry_per_capita": 7,
        "food_per_capita": 7,
        "pollution_pressure": 3,
        "human_welfare": 5,
    }:
        fail(f"Unexpected empirical projection-support scores: {expected_support}")

    print("Validare statică reușită: BAU Hibrid 2026 v0.10.0, două punți de observație validate pre-2019, cuantile autentice, 128 candidați, 12 rulări admisibile și 8 grafice.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ET.ParseError) as error:
        print(f"Eroare de validare: {error}", file=sys.stderr)
        raise SystemExit(1)
