"""Test whether lookup-domain guardrails improve temporal validation.

The official World3-03 lookup tables are constant outside their tabulated
domains when executed by PySD.  That behaviour is legitimate but weakens the
interpretation of candidate trajectories that spend long periods far beyond a
table boundary.  This audit tests whether a simple, temporally honest filter on
those events improves out-of-sample performance.  It never changes the
production model directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_joint_hybrid_2026 import (
    VALIDATION_SEGMENTS,
    apply_observation_bridges,
    build_indicators,
    parameter_candidates,
    run_candidates,
    score_candidate,
    select_candidates,
)


ROOT = Path(__file__).resolve().parents[1]
JOINT_OUTPUT = ROOT / "outputs" / "joint_hybrid_2026"
OUTPUT = ROOT / "outputs" / "lookup_domain_guardrail"
ORIGINS = (2005, 2010, 2015, 2018)
DEVELOPMENT_ORIGINS = (2005, 2010, 2015)
INDEPENDENT_ORIGIN = 2018
LOOKUP_WINDOW_START = 1970
MATERIAL_DISTANCE_THRESHOLD = 0.05
METRICS = ("events", "material_events", "distance_exposure", "lookups")
RETENTION_QUANTILES = (0.25, 0.50, 0.75, 0.90)
MINIMUM_AGGREGATE_IMPROVEMENT_PCT = 5.0
MAXIMUM_SECTOR_WORSENING_PCT = 10.0


def lookup_metrics(candidate_count: int) -> pd.DataFrame:
    """Return candidate diagnostics available at each forecast origin.

    Scenario-switch tables are excluded because their inputs deliberately
    encode dates and switches rather than a causal state variable.  Only
    events at or before the origin can affect selection at that origin.
    """

    context = pd.read_csv(JOINT_OUTPUT / "lookup_extrapolation_context.csv")
    causal = context.loc[
        ~context["lookup"].str.contains("scenario_table", case=False, na=False)
        & context["year"].ge(LOOKUP_WINDOW_START)
    ].copy()
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

    rows: list[pd.DataFrame] = []
    for origin in ORIGINS:
        available = causal.loc[causal["year"].le(origin)]
        aggregate = available.groupby("candidate_id").agg(
            events=("count", "sum"),
            material_events=("material_count", "sum"),
            distance_exposure=("distance_exposure_component", "sum"),
            lookups=("lookup", "nunique"),
        )
        aggregate = aggregate.reindex(range(candidate_count), fill_value=0)
        aggregate.insert(0, "origin", origin)
        aggregate.insert(1, "lookup_information_cutoff", origin)
        rows.append(aggregate.reset_index())
    return pd.concat(rows, ignore_index=True)


def candidate_rankings(candidates, indicators) -> dict[int, pd.DataFrame | None]:
    """Calculate each temporal ranking once and reuse it for every policy."""

    rankings: dict[int, pd.DataFrame | None] = {}
    for origin in ORIGINS:
        available_segments = tuple(
            segment for segment in VALIDATION_SEGMENTS if segment[1] <= origin
        )
        rankings[origin] = (
            select_candidates(candidates, indicators, origin, available_segments)
            if available_segments
            else None
        )
    return rankings


def selected_candidate(
    origin: int,
    ranking: pd.DataFrame | None,
    metrics: pd.DataFrame,
    metric: str | None,
    quantile: float | None,
) -> tuple[int, float | None, int]:
    """Select the best mapped candidate after an optional lookup filter."""

    if ranking is None:
        return 0, None, 1
    admissible = ranking.loc[ranking["mapping_boundary_count"].eq(0)]
    if metric is None:
        return int(admissible.iloc[0]["candidate_id"]), None, len(admissible)

    at_origin = metrics.loc[metrics["origin"].eq(origin)].set_index("candidate_id")
    threshold = float(at_origin[metric].quantile(float(quantile)))
    retained_ids = set(at_origin.index[at_origin[metric].le(threshold)])
    filtered = admissible.loc[admissible["candidate_id"].isin(retained_ids)]
    if filtered.empty:
        raise RuntimeError(
            f"Lookup policy {metric} q={quantile} retained no mapped candidate "
            f"at origin {origin}"
        )
    return int(filtered.iloc[0]["candidate_id"]), threshold, len(filtered)


def evaluate_policy(
    name: str,
    metric: str | None,
    quantile: float | None,
    bridged_candidates,
    indicators,
    rankings: dict[int, pd.DataFrame | None],
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    records = []
    for origin in ORIGINS:
        candidate_id, threshold, retained = selected_candidate(
            origin, rankings[origin], metrics, metric, quantile
        )
        candidate = bridged_candidates[candidate_id]
        _, _, scales, _ = score_candidate(candidate, indicators, origin)
        for indicator in indicators:
            observed = indicator.observed.loc[
                indicator.observed.index > origin
            ].dropna()
            if observed.empty:
                continue
            predicted = (
                scales[indicator.key] * candidate.simulation[indicator.key]
            ).reindex(observed.index)
            log_rmse = float(
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
            records.append(
                {
                    "policy": name,
                    "metric": metric or "none",
                    "retention_quantile": quantile,
                    "origin": origin,
                    "lookup_information_cutoff": origin,
                    "evaluation_start": int(observed.index.min()),
                    "evaluation_end": int(observed.index.max()),
                    "indicator": indicator.key,
                    "n": int(len(observed)),
                    "selected_candidate_id": candidate_id,
                    "metric_threshold": threshold,
                    "retained_mapped_candidates": retained,
                    "log_rmse": log_rmse,
                }
            )
    return pd.DataFrame(records)


def pooled_score(frame: pd.DataFrame, origins: tuple[int, ...]) -> float:
    selected = frame.loc[frame["origin"].isin(origins)]
    return float(
        np.sqrt(
            np.average(
                np.square(selected["log_rmse"].to_numpy(dtype=float)),
                weights=selected["n"].to_numpy(dtype=float),
            )
        )
    )


def summarize_policy(frame: pd.DataFrame, baseline: pd.DataFrame) -> dict[str, object]:
    development = pooled_score(frame, DEVELOPMENT_ORIGINS)
    development_baseline = pooled_score(baseline, DEVELOPMENT_ORIGINS)
    independent = pooled_score(frame, (INDEPENDENT_ORIGIN,))
    independent_baseline = pooled_score(baseline, (INDEPENDENT_ORIGIN,))
    development_improvement = 100.0 * (
        development_baseline - development
    ) / development_baseline
    independent_improvement = 100.0 * (
        independent_baseline - independent
    ) / independent_baseline

    test = frame.loc[frame["origin"].eq(INDEPENDENT_ORIGIN)].set_index("indicator")
    test_baseline = baseline.loc[
        baseline["origin"].eq(INDEPENDENT_ORIGIN)
    ].set_index("indicator")
    sector_improvement = 100.0 * (
        test_baseline["log_rmse"] - test["log_rmse"]
    ) / test_baseline["log_rmse"]
    maximum_sector_worsening = float(max(0.0, -sector_improvement.min()))
    accepted = bool(
        development_improvement >= MINIMUM_AGGREGATE_IMPROVEMENT_PCT
        and independent_improvement >= MINIMUM_AGGREGATE_IMPROVEMENT_PCT
        and maximum_sector_worsening <= MAXIMUM_SECTOR_WORSENING_PCT
    )
    ids = frame.groupby("origin")["selected_candidate_id"].first().to_dict()
    return {
        "policy": frame.iloc[0]["policy"],
        "metric": frame.iloc[0]["metric"],
        "retention_quantile": frame.iloc[0]["retention_quantile"],
        "feasible": True,
        "infeasible_reason": "",
        "development_log_rmse": development,
        "development_improvement_pct": development_improvement,
        "independent_log_rmse": independent,
        "independent_improvement_pct": independent_improvement,
        "maximum_independent_sector_worsening_pct": maximum_sector_worsening,
        "selected_candidate_ids": json.dumps(
            {str(key): int(value) for key, value in ids.items()}, sort_keys=True
        ),
        "accepted": accepted,
    }


def main() -> None:
    indicators, _ = build_indicators()
    candidates = run_candidates(parameter_candidates())
    bridged_candidates = apply_observation_bridges(candidates)
    metrics = lookup_metrics(len(candidates))
    rankings = candidate_rankings(candidates, indicators)

    baseline = evaluate_policy(
        "baseline", None, None, bridged_candidates, indicators, rankings, metrics
    )
    policy_frames = []
    summary_records = []
    for metric in METRICS:
        for quantile in RETENTION_QUANTILES:
            name = f"{metric}_q{int(100 * quantile):02d}"
            try:
                frame = evaluate_policy(
                    name,
                    metric,
                    quantile,
                    bridged_candidates,
                    indicators,
                    rankings,
                    metrics,
                )
            except RuntimeError as error:
                summary_records.append(
                    {
                        "policy": name,
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
            policy_frames.append(frame)
            summary_records.append(summarize_policy(frame, baseline))

    summary = pd.DataFrame(summary_records).sort_values(
        ["development_log_rmse", "policy"]
    )
    feasible_summary = summary.loc[summary["feasible"]]
    if feasible_summary.empty:
        raise RuntimeError("No lookup-domain policy is feasible at every origin")
    chosen = feasible_summary.iloc[0]
    chosen_frame = next(
        frame for frame in policy_frames if frame.iloc[0]["policy"] == chosen["policy"]
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
        rejection_reasons.append("independent improvement below 5%")
    if float(chosen["maximum_independent_sector_worsening_pct"]) > MAXIMUM_SECTOR_WORSENING_PCT:
        rejection_reasons.append("an independent sector worsened by more than 10%")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUTPUT / "candidate_lookup_metrics.csv", index=False)
    pd.concat([baseline, *policy_frames], ignore_index=True).to_csv(
        OUTPUT / "policy_backtest.csv", index=False
    )
    summary.to_csv(OUTPUT / "policy_summary.csv", index=False)
    comparison.to_csv(OUTPUT / "chosen_policy_comparison.csv", index=False)
    manifest = {
        "audit": "World3-03 lookup-domain candidate selection guardrail",
        "status": "accepted" if accepted else "rejected",
        "production_decision": (
            "eligible_for_future_joint_refit"
            if accepted
            else "do_not_change_BAU_Hybrid_2026_v0.10.0"
        ),
        "lookup_window_start": LOOKUP_WINDOW_START,
        "origins": list(ORIGINS),
        "development_origins": list(DEVELOPMENT_ORIGINS),
        "independent_origin": INDEPENDENT_ORIGIN,
        "temporal_comparison_reused_across_project_audits": True,
        "scenario_switch_lookups_excluded": True,
        "candidate_count": len(candidates),
        "policies_screened": len(METRICS) * len(RETENTION_QUANTILES),
        "policies_feasible": len(policy_frames),
        "metrics": list(METRICS),
        "retention_quantiles": list(RETENTION_QUANTILES),
        "chosen_on_development_only": str(chosen["policy"]),
        "chosen_development_improvement_pct": float(
            chosen["development_improvement_pct"]
        ),
        "chosen_independent_improvement_pct": float(
            chosen["independent_improvement_pct"]
        ),
        "chosen_maximum_independent_sector_worsening_pct": float(
            chosen["maximum_independent_sector_worsening_pct"]
        ),
        "acceptance_rule": {
            "minimum_development_improvement_pct": MINIMUM_AGGREGATE_IMPROVEMENT_PCT,
            "minimum_independent_improvement_pct": MINIMUM_AGGREGATE_IMPROVEMENT_PCT,
            "maximum_independent_sector_worsening_pct": MAXIMUM_SECTOR_WORSENING_PCT,
        },
        "rejection_reasons": rejection_reasons,
        "interpretation": (
            "Lookup-domain distance is a useful validity diagnostic, but this "
            "screening rule is not a validated selection improvement."
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
    print(summary.to_string(index=False), flush=True)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
