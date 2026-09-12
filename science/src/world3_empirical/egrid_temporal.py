"""Release-lagged eGRID plant-panel stability diagnostics.

This module evaluates year-to-year stability after both target years are known.
It is deliberately not described as a real-time forecast backtest because eGRID
editions are released after their data years.
"""
from collections import Counter
import math

KG_PER_SHORT_TON = 907.18474


def _index(rows, expected_year):
    indexed = {}
    for row in rows:
        required = ("YEAR", "ORISPL", "PLNGENAN", "UNHTI", "UNCO2", "UNCO2SRC", "UNHTISRC")
        if any(field not in row for field in required):
            raise ValueError("Temporal cohort is missing a required field")
        if row["YEAR"] != expected_year:
            raise ValueError("Cohort contains an unexpected year")
        plant = row["ORISPL"]
        if isinstance(plant, bool) or not isinstance(plant, (float, int)):
            raise ValueError("Invalid plant identifier")
        for field in ("PLNGENAN", "UNHTI", "UNCO2"):
            value = row[field]
            if (
                isinstance(value, bool)
                or not isinstance(value, (float, int))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError("Temporal cohort contains an invalid physical quantity")
        if not isinstance(row["UNCO2SRC"], str) or not isinstance(row["UNHTISRC"], str):
            raise ValueError("Temporal cohort contains invalid provenance")
        if plant in indexed:
            raise ValueError("Duplicate plant-year")
        indexed[plant] = row
    if not indexed:
        raise ValueError("Empty cohort")
    return indexed


def _source_family(source):
    parts = set(source.replace("EPA/CAMD", "EPA").replace("EPA/CAPD", "EPA").split("; "))
    return "+".join(sorted(parts))


def _signal_metrics(training, target, plants, quantity, conversion):
    train_generation = sum(training[p]["PLNGENAN"] for p in plants)
    target_generation = sum(target[p]["PLNGENAN"] for p in plants)
    train_quantity = sum(training[p][quantity] for p in plants)
    target_quantity = sum(target[p][quantity] for p in plants)
    train_intensity = conversion * train_quantity / train_generation
    target_intensity = conversion * target_quantity / target_generation

    persistence_predictions = {}
    mean_predictions = {}
    for plant in plants:
        plant_train_intensity = conversion * training[plant][quantity] / training[plant]["PLNGENAN"]
        persistence_predictions[plant] = (
            plant_train_intensity / conversion * target[plant]["PLNGENAN"]
        )
        mean_predictions[plant] = train_intensity / conversion * target[plant]["PLNGENAN"]

    def score(predictions):
        predicted_total = sum(predictions.values())
        wmape = 100 * sum(
            abs(predictions[p] - target[p][quantity]) for p in plants
        ) / target_quantity
        return {
            "aggregate_bias_pct": 100 * (predicted_total / target_quantity - 1),
            "quantity_weighted_absolute_percentage_error_pct": wmape,
        }

    persistence = score(persistence_predictions)
    cohort_mean = score(mean_predictions)
    baseline_wmape = cohort_mean["quantity_weighted_absolute_percentage_error_pct"]
    persistence_wmape = persistence["quantity_weighted_absolute_percentage_error_pct"]
    persistence["wmape_change_defined"] = baseline_wmape > 0
    persistence["wmape_change_vs_cohort_mean_pct"] = (
        100 * (persistence_wmape / baseline_wmape - 1)
        if baseline_wmape > 0 else (0.0 if persistence_wmape == 0 else None)
    )
    return {
        "training_aggregate_intensity": train_intensity,
        "target_aggregate_intensity": target_intensity,
        "aggregate_intensity_change_pct": 100 * (target_intensity / train_intensity - 1),
        "plant_specific_persistence": persistence,
        "training_cohort_mean_persistence": cohort_mean,
    }


def temporal_stability_audit(training_rows, target_rows, training_year, target_year):
    if target_year != training_year + 1:
        raise ValueError("Years must be consecutive")
    training = _index(training_rows, training_year)
    target = _index(target_rows, target_year)
    plants = sorted(training.keys() & target.keys())
    if not plants:
        raise ValueError("No plants are present in both cohorts")

    target_generation_all = sum(row["PLNGENAN"] for row in target.values())
    target_generation_matched = sum(target[p]["PLNGENAN"] for p in plants)
    raw_transitions = Counter()
    family_transitions = Counter()
    for plant in plants:
        old = training[plant]
        new = target[plant]
        raw_old = old["UNCO2SRC"] + " | " + old["UNHTISRC"]
        raw_new = new["UNCO2SRC"] + " | " + new["UNHTISRC"]
        raw_transitions[raw_old + " -> " + raw_new] += 1
        family_old = _source_family(old["UNCO2SRC"]) + " | " + _source_family(old["UNHTISRC"])
        family_new = _source_family(new["UNCO2SRC"]) + " | " + _source_family(new["UNHTISRC"])
        family_transitions[family_old + " -> " + family_new] += 1

    result = {
        "training_year": training_year,
        "target_year": target_year,
        "eligible_training_plants": len(training),
        "eligible_target_plants": len(target),
        "matched_plants": len(plants),
        "exiting_plants": len(training.keys() - target.keys()),
        "entering_plants": len(target.keys() - training.keys()),
        "matched_share_of_target_generation_pct": 100 * target_generation_matched / target_generation_all,
        "raw_source_transitions": dict(sorted(raw_transitions.items())),
        "normalized_source_family_transitions": dict(sorted(family_transitions.items())),
        "signals": {
            "heat_rate_btu_per_net_kwh": _signal_metrics(training, target, plants, "UNHTI", 1000),
            "co2_kg_per_net_mwh": _signal_metrics(training, target, plants, "UNCO2", KG_PER_SHORT_TON),
        },
        "interpretation": (
            "Release-lagged matched-panel stability audit conditional on target-year generation; "
            "not a real-time forecast backtest and not evidence for changing BAU Hibrid 2026."
        ),
    }
    for signal in result["signals"].values():
        for value in _walk_numbers(signal):
            if not math.isfinite(value):
                raise ValueError("Non-finite temporal metric")
    return result


def _walk_numbers(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _walk_numbers(nested)
    elif isinstance(value, (float, int)) and not isinstance(value, bool):
        yield value
