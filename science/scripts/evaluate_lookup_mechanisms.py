"""Audit World3 lookup-domain extrapolations by causal mechanism.

The generic lookup audit showed that total warning counts are not a validated
candidate-selection guardrail.  This follow-up keeps distinct causal families
separate, chooses one predeclared family policy using development origins only,
and then reports its performance at the reused 2018 temporal comparison.
Nothing in this script changes the production projection.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_joint_hybrid_2026 import (
    apply_observation_bridges,
    build_indicators,
    parameter_candidates,
    run_candidates,
)
from evaluate_lookup_domain_guardrail import (
    DEVELOPMENT_ORIGINS,
    INDEPENDENT_ORIGIN,
    LOOKUP_WINDOW_START,
    MATERIAL_DISTANCE_THRESHOLD,
    MAXIMUM_SECTOR_WORSENING_PCT,
    MINIMUM_AGGREGATE_IMPROVEMENT_PCT,
    ORIGINS,
    candidate_rankings,
    evaluate_policy,
    summarize_policy,
)


ROOT = Path(__file__).resolve().parents[1]
JOINT_OUTPUT = ROOT / "outputs" / "joint_hybrid_2026"
OUTPUT = ROOT / "outputs" / "lookup_mechanisms"
METRICS = ("events", "material_events", "distance_exposure")
RETENTION_QUANTILES = (0.25, 0.50)

# Each causal lookup is assigned once according to its role in the stock-flow
# model, not the indicator against which a candidate happens to score well.
LOOKUP_MECHANISMS = {
    "_hardcodedlookup_capacity_utilization_fraction_table": (
        "labor_capacity",
        "delayed labor utilization fraction",
    ),
    "_hardcodedlookup_jobs_per_hectare_table": (
        "labor_capacity",
        "agricultural input per hectare",
    ),
    "_hardcodedlookup_jobs_per_industrial_capital_unit_table": (
        "labor_capacity",
        "industrial output per capita",
    ),
    "_hardcodedlookup_jobs_per_service_capital_unit_table": (
        "labor_capacity",
        "service output per capita",
    ),
    "_hardcodedlookup_fraction_industrial_output_allocated_to_agriculture_table_1": (
        "agriculture_land_food",
        "food relative to indicated food",
    ),
    "_hardcodedlookup_fraction_of_agricultural_inputs_for_land_maintenance_table": (
        "agriculture_land_food",
        "perceived food ratio",
    ),
    "_hardcodedlookup_indicated_food_per_capita_table_1": (
        "agriculture_land_food",
        "industrial output per capita",
    ),
    "_hardcodedlookup_land_life_multiplier_from_land_yield_table_1": (
        "agriculture_land_food",
        "land yield relative to inherent fertility",
    ),
    "_hardcodedlookup_land_yield_multiplier_from_capital_table": (
        "agriculture_land_food",
        "agricultural input per hectare",
    ),
    "_hardcodedlookup_marginal_land_yield_multiplier_from_capital_table": (
        "agriculture_land_food",
        "agricultural input per hectare",
    ),
    "_hardcodedlookup_assimilation_half_life_mult_table": (
        "pollution_ecology",
        "persistent pollution index",
    ),
    "_hardcodedlookup_land_fertility_degredation_rate_table": (
        "pollution_ecology",
        "persistent pollution index",
    ),
    "_hardcodedlookup_lifetime_multiplier_from_persistent_pollution_table": (
        "pollution_ecology",
        "persistent pollution index",
    ),
    "_hardcodedlookup_health_services_per_capita_table": (
        "health_mortality",
        "service output per capita",
    ),
    "_hardcodedlookup_life_expectancy_index_lookup": (
        "health_mortality",
        "life expectancy",
    ),
    "_hardcodedlookup_lifetime_multiplier_from_food_table": (
        "health_mortality",
        "food relative to subsistence",
    ),
    "_hardcodedlookup_lifetime_multiplier_from_health_services_2_table": (
        "health_mortality",
        "effective health services per capita",
    ),
    "_hardcodedlookup_mortality_0_to_14_table": (
        "health_mortality",
        "life expectancy",
    ),
    "_hardcodedlookup_mortality_15_to_44_table": (
        "health_mortality",
        "life expectancy",
    ),
    "_hardcodedlookup_mortality_45_to_64_table": (
        "health_mortality",
        "life expectancy",
    ),
    "_hardcodedlookup_mortality_65_plus_table": (
        "health_mortality",
        "life expectancy",
    ),
    "_hardcodedlookup_completed_multiplier_from_perceived_lifetime_table": (
        "fertility_social_response",
        "perceived life expectancy",
    ),
    "_hardcodedlookup_family_response_to_social_norm_table": (
        "fertility_social_response",
        "family income expectation",
    ),
    "_hardcodedlookup_fecundity_multiplier_table": (
        "fertility_social_response",
        "life expectancy",
    ),
    "_hardcodedlookup_fertility_control_effectiveness_table": (
        "fertility_social_response",
        "fertility control facilities per capita",
    ),
    "_hardcodedlookup_fraction_services_allocated_to_fertility_control_table": (
        "fertility_social_response",
        "need for fertility control",
    ),
    "_hardcodedlookup_social_family_size_normal_table": (
        "fertility_social_response",
        "delayed industrial output per capita",
    ),
    "_hardcodedlookup_crowding_multiplier_from_industry_table": (
        "affluence_material_demand",
        "industrial output per capita",
    ),
    "_hardcodedlookup_fraction_of_industrial_output_allocated_to_services_table_1": (
        "affluence_material_demand",
        "service output relative to indicated services",
    ),
    "_hardcodedlookup_gdp_per_capita_lookup": (
        "affluence_material_demand",
        "industrial output per capita",
    ),
    "_hardcodedlookup_indicated_services_output_per_capita_table_1": (
        "affluence_material_demand",
        "industrial output per capita",
    ),
    "_hardcodedlookup_per_capita_resource_use_mult_table": (
        "affluence_material_demand",
        "industrial output per capita",
    ),
    "_hardcodedlookup_urban_and_industrial_land_required_per_capita_table": (
        "affluence_material_demand",
        "industrial output per capita",
    ),
}
MECHANISMS = tuple(sorted({value[0] for value in LOOKUP_MECHANISMS.values()}))


def causal_context() -> pd.DataFrame:
    context = pd.read_csv(JOINT_OUTPUT / "lookup_extrapolation_context.csv")
    causal = context.loc[
        ~context["lookup"].str.contains("scenario_table", case=False, na=False)
        & context["year"].ge(LOOKUP_WINDOW_START)
    ].copy()
    observed = set(causal["lookup"])
    expected = set(LOOKUP_MECHANISMS)
    if observed != expected:
        missing = sorted(observed - expected)
        obsolete = sorted(expected - observed)
        raise RuntimeError(
            f"Lookup taxonomy mismatch; unclassified={missing}; absent={obsolete}"
        )
    causal["mechanism"] = causal["lookup"].map(
        {key: value[0] for key, value in LOOKUP_MECHANISMS.items()}
    )
    causal["material_count"] = np.where(
        causal["furthest_boundary_distance_normalized"].ge(
            MATERIAL_DISTANCE_THRESHOLD
        ),
        causal["count"],
        0,
    )
    causal["distance_exposure_component"] = causal["count"] * np.log1p(
        causal["furthest_boundary_distance_normalized"].clip(lower=0.0)
    )
    return causal


def mechanism_mapping() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"lookup": lookup, "mechanism": values[0], "driver": values[1]}
            for lookup, values in sorted(LOOKUP_MECHANISMS.items())
        ]
    )


def mechanism_metrics(context: pd.DataFrame, candidate_count: int) -> pd.DataFrame:
    rows = []
    complete_index = pd.MultiIndex.from_product(
        [range(candidate_count), MECHANISMS], names=("candidate_id", "mechanism")
    )
    for origin in ORIGINS:
        available = context.loc[context["year"].le(origin)]
        aggregate = available.groupby(["candidate_id", "mechanism"]).agg(
            events=("count", "sum"),
            material_events=("material_count", "sum"),
            distance_exposure=("distance_exposure_component", "sum"),
            lookups=("lookup", "nunique"),
        )
        aggregate = aggregate.reindex(complete_index, fill_value=0).reset_index()
        aggregate.insert(0, "origin", origin)
        aggregate.insert(1, "lookup_information_cutoff", origin)
        rows.append(aggregate)
    return pd.concat(rows, ignore_index=True)


def central_inventory(context: pd.DataFrame, central_id: int = 114) -> pd.DataFrame:
    central = context.loc[context["candidate_id"].eq(central_id)].copy()
    central["post_2025_count"] = np.where(
        central["year"].gt(2025), central["count"], 0
    )
    central["post_2025_material_count"] = np.where(
        central["year"].gt(2025), central["material_count"], 0
    )
    return (
        central.groupby("mechanism")
        .agg(
            events=("count", "sum"),
            material_events=("material_count", "sum"),
            distinct_lookups=("lookup", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
            maximum_normalized_distance=(
                "furthest_boundary_distance_normalized",
                "max",
            ),
            post_2025_events=("post_2025_count", "sum"),
            post_2025_material_events=("post_2025_material_count", "sum"),
        )
        .reindex(MECHANISMS, fill_value=0)
        .reset_index()
    )


def main() -> None:
    indicators, _ = build_indicators()
    candidates = run_candidates(parameter_candidates())
    bridged = apply_observation_bridges(candidates)
    rankings = candidate_rankings(candidates, indicators)
    context = causal_context()
    metrics = mechanism_metrics(context, len(candidates))

    baseline = evaluate_policy(
        "baseline", None, None, bridged, indicators, rankings, metrics
    )
    frames = []
    summaries = []
    for mechanism in MECHANISMS:
        mechanism_metrics_frame = metrics.loc[
            metrics["mechanism"].eq(mechanism)
        ].drop(columns="mechanism")
        for metric in METRICS:
            for quantile in RETENTION_QUANTILES:
                name = f"{mechanism}__{metric}_q{int(quantile * 100):02d}"
                try:
                    frame = evaluate_policy(
                        name,
                        metric,
                        quantile,
                        bridged,
                        indicators,
                        rankings,
                        mechanism_metrics_frame,
                    )
                except RuntimeError as error:
                    summaries.append(
                        {
                            "policy": name,
                            "mechanism": mechanism,
                            "metric": metric,
                            "retention_quantile": quantile,
                            "feasible": False,
                            "infeasible_reason": str(error),
                            "development_log_rmse": np.nan,
                            "development_improvement_pct": np.nan,
                            "independent_log_rmse": np.nan,
                            "independent_improvement_pct": np.nan,
                            "maximum_independent_sector_worsening_pct": np.nan,
                            "selected_candidate_ids": "{}",
                            "accepted": False,
                        }
                    )
                    continue
                summary = summarize_policy(frame, baseline)
                summary["mechanism"] = mechanism
                frames.append(frame.assign(mechanism=mechanism))
                summaries.append(summary)

    summary = pd.DataFrame(summaries).sort_values(
        ["development_log_rmse", "policy"]
    )
    feasible = summary.loc[summary["feasible"]]
    if feasible.empty:
        raise RuntimeError("No mechanism-level lookup policy is feasible")
    chosen = feasible.iloc[0]
    chosen_frame = next(
        frame for frame in frames if frame.iloc[0]["policy"] == chosen["policy"]
    )
    comparison = chosen_frame.merge(
        baseline[["origin", "indicator", "selected_candidate_id", "log_rmse"]],
        on=["origin", "indicator"],
        suffixes=("_policy", "_baseline"),
    )
    comparison["improvement_pct"] = 100.0 * (
        comparison["log_rmse_baseline"] - comparison["log_rmse_policy"]
    ) / comparison["log_rmse_baseline"]

    accepted = bool(chosen["accepted"])
    rejection_reasons = []
    if float(chosen["development_improvement_pct"]) < MINIMUM_AGGREGATE_IMPROVEMENT_PCT:
        rejection_reasons.append("development improvement below 5%")
    if float(chosen["independent_improvement_pct"]) < MINIMUM_AGGREGATE_IMPROVEMENT_PCT:
        rejection_reasons.append("temporal comparison improvement below 5%")
    if float(chosen["maximum_independent_sector_worsening_pct"]) > MAXIMUM_SECTOR_WORSENING_PCT:
        rejection_reasons.append("a temporal-comparison sector worsened by more than 10%")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mechanism_mapping().to_csv(OUTPUT / "lookup_mechanism_mapping.csv", index=False)
    metrics.to_csv(OUTPUT / "candidate_mechanism_metrics.csv", index=False)
    central_inventory(context).to_csv(
        OUTPUT / "central_mechanism_inventory.csv", index=False
    )
    pd.concat([baseline.assign(mechanism="none"), *frames], ignore_index=True).to_csv(
        OUTPUT / "policy_backtest.csv", index=False
    )
    summary.to_csv(OUTPUT / "policy_summary.csv", index=False)
    comparison.to_csv(OUTPUT / "chosen_policy_comparison.csv", index=False)

    manifest = {
        "audit": "World3-03 mechanism-specific lookup-domain guardrails",
        "status": "accepted" if accepted else "rejected",
        "production_decision": (
            "eligible_for_future_joint_refit"
            if accepted
            else "do_not_change_BAU_Hybrid_2026_v0.10.0"
        ),
        "taxonomy_frozen_before_policy_evaluation": True,
        "mechanisms": list(MECHANISMS),
        "lookup_count": len(LOOKUP_MECHANISMS),
        "origins": list(ORIGINS),
        "development_origins": list(DEVELOPMENT_ORIGINS),
        "temporal_comparison_origin": INDEPENDENT_ORIGIN,
        "temporal_comparison_reused_across_project_audits": True,
        "candidate_count": len(candidates),
        "policies_screened": len(MECHANISMS)
        * len(METRICS)
        * len(RETENTION_QUANTILES),
        "policies_feasible": int(feasible.shape[0]),
        "chosen_on_development_only": str(chosen["policy"]),
        "chosen_mechanism": str(chosen["mechanism"]),
        "chosen_development_improvement_pct": float(
            chosen["development_improvement_pct"]
        ),
        "chosen_temporal_comparison_improvement_pct": float(
            chosen["independent_improvement_pct"]
        ),
        "chosen_maximum_temporal_sector_worsening_pct": float(
            chosen["maximum_independent_sector_worsening_pct"]
        ),
        "acceptance_rule": {
            "minimum_development_improvement_pct": MINIMUM_AGGREGATE_IMPROVEMENT_PCT,
            "minimum_temporal_comparison_improvement_pct": MINIMUM_AGGREGATE_IMPROVEMENT_PCT,
            "maximum_temporal_sector_worsening_pct": MAXIMUM_SECTOR_WORSENING_PCT,
        },
        "rejection_reasons": rejection_reasons,
        "tie_break_rule": (
            "minimum development log-RMSE, then lexical policy name; temporal "
            "comparison scores never break a development tie"
        ),
        "interpretation_limit": (
            "The 2018-origin comparison is temporally separated from policy "
            "selection but has been reused by earlier project audits; it is not "
            "a globally untouched confirmatory holdout."
        ),
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(central_inventory(context).to_string(index=False), flush=True)
    print(summary.to_string(index=False), flush=True)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
