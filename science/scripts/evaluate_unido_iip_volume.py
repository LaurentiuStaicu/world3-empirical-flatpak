"""Prospective audit of UNIDO real manufacturing output as the industry target.

The audit changes one observation equation only.  It retains the 128 World3
candidates, structural equations, validation windows and all non-industry
targets.  Its public-data world IIP is diagnostic because UNIDO's unpublished
country imputations cannot be reproduced and manufacturing is narrower than
World3 industrial output.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_bau2_e2026 import Indicator, build_indicators
from build_joint_hybrid_2026 import (
    CACHE,
    Candidate,
    PRODUCTION_SEGMENTS,
    SIMULATION_KEYS,
    VALIDATION_SEGMENTS,
    YEARS,
    add_plausibility_columns,
    apply_observation_bridges,
    observation_mapping,
    parameter_candidates,
    score_candidate,
    select_candidates,
    select_medoid,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "unido_iip_world_public_2026-09-08.csv"
PROVENANCE = DATA.with_suffix(".provenance.json")
UNIDO_MVA = ROOT / "data" / "processed" / "unido_national_accounts_world_2026-09-07.csv"
HYBRID = ROOT / "outputs" / "joint_hybrid_2026"
OUTPUT = ROOT / "outputs" / "unido_iip_volume"
ORIGINS = (2014, 2018)
TEMPORAL_COMPARISON_ORIGIN = 2018
MINIMUM_IIP_IMPROVEMENT_PCT = 5.0
MAXIMUM_NONINDUSTRY_POOLED_WORSENING_PCT = 5.0
MAXIMUM_NONINDUSTRY_SECTOR_WORSENING_PCT = 10.0
MINIMUM_MVA_WEIGHT_COVERAGE_PCT = 90.0
IIP_PRODUCTION_SEGMENTS = tuple(
    segment for segment in PRODUCTION_SEGMENTS if segment[0] >= 2010
)


def iip_per_capita() -> pd.Series:
    frame = pd.read_csv(DATA).set_index("year")
    return frame["manufacturing_iip_per_capita_index_2015"].dropna()


def replace_industry(indicators: list[Indicator], observed: pd.Series) -> list[Indicator]:
    result = []
    for indicator in indicators:
        if indicator.key != "industry_per_capita":
            result.append(indicator)
            continue
        result.append(
            replace(
                indicator,
                observed=observed,
                unit="UNIDO manufacturing IIP/locuitor, indice 2015=100",
                source="UNIDO IIP public balanced panel; fixed 2020 MVA weights",
                source_url="https://stat.unido.org/portal/dataset/getDataset/IIP",
                status=(
                    "reconstrucție publică 2005–2025; producție brută reală, "
                    "fără imputările naționale nepublicate de UNIDO"
                ),
            )
        )
    return result


def selected_id(candidates, indicators: list[Indicator], origin: int) -> int:
    segments = tuple(
        segment for segment in VALIDATION_SEGMENTS
        if segment[0] >= 2010 and segment[1] <= origin
    )
    ranking = select_candidates(candidates, indicators, origin, segments)
    eligible = ranking.loc[ranking["mapping_boundary_count"].eq(0)]
    return int((eligible if not eligible.empty else ranking).iloc[0]["candidate_id"])


def load_candidates_fast(candidate_values: np.ndarray) -> list[Candidate]:
    """Load the frozen simulations without rewriting the large lookup audit."""
    with np.load(CACHE) as cached:
        if cached["values"].shape != candidate_values.shape or not np.allclose(
            cached["values"], candidate_values
        ):
            raise RuntimeError("Cached candidate simulations do not match the design")
        return [
            Candidate(
                candidate_id,
                values,
                {
                    key: pd.Series(
                        cached[f"series_{key}"][candidate_id],
                        index=YEARS.astype(int),
                        dtype=float,
                    )
                    for key in SIMULATION_KEYS
                },
            )
            for candidate_id, values in enumerate(candidate_values)
        ]


def metrics(observed: pd.Series, predicted: pd.Series) -> tuple[float, float]:
    overlap = observed.index.intersection(predicted.index)
    ratio = predicted.loc[overlap].to_numpy(dtype=float) / observed.loc[overlap].to_numpy(dtype=float)
    return float(np.sqrt(np.mean(np.square(np.log(ratio))))), float(100.0 * np.mean(np.abs(ratio - 1.0)))


def forecast(candidate, indicator: Indicator, origin: int) -> tuple[pd.Series, pd.Series]:
    observed = indicator.observed.loc[indicator.observed.index > origin].dropna()
    scale, _ = observation_mapping(indicator, candidate.simulation[indicator.key], origin)
    return observed, scale * candidate.simulation[indicator.key].reindex(observed.index)


def backtests(candidates, current: list[Indicator], alternative: list[Indicator]):
    configurations = {"world_bank_industry": current, "unido_iip_volume": alternative}
    industry = {
        name: next(item for item in indicators if item.key == "industry_per_capita")
        for name, indicators in configurations.items()
    }
    proxy_rows, system_rows = [], []
    for origin in ORIGINS:
        selected = {
            name: selected_id(candidates, indicators, origin)
            for name, indicators in configurations.items()
        }
        for selector, candidate_id in selected.items():
            candidate = candidates[candidate_id]
            for evaluation, indicator in industry.items():
                observed, predicted = forecast(candidate, indicator, origin)
                log_rmse, mape_pct = metrics(observed, predicted)
                proxy_rows.append({
                    "origin": origin,
                    "selector_proxy": selector,
                    "evaluation_proxy": evaluation,
                    "selected_candidate_id": candidate_id,
                    "evaluation_start": int(observed.index.min()),
                    "evaluation_end": int(observed.index.max()),
                    "n": len(observed),
                    "log_rmse": log_rmse,
                    "mape_pct": mape_pct,
                })
            for indicator in current:
                if indicator.key == "industry_per_capita":
                    continue
                observed, predicted = forecast(candidate, indicator, origin)
                log_rmse, mape_pct = metrics(observed, predicted)
                system_rows.append({
                    "origin": origin,
                    "selector_proxy": selector,
                    "indicator": indicator.key,
                    "selected_candidate_id": candidate_id,
                    "n": len(observed),
                    "log_rmse": log_rmse,
                    "mape_pct": mape_pct,
                })
    return pd.DataFrame(proxy_rows), pd.DataFrame(system_rows)


def observed_comparison(current: list[Indicator], alternative: list[Indicator]):
    wb = next(item.observed for item in current if item.key == "industry_per_capita")
    iip = next(item.observed for item in alternative if item.key == "industry_per_capita")
    overlap = wb.index.intersection(iip.index)
    mva_frame = pd.read_csv(UNIDO_MVA).set_index("year")
    mva = mva_frame["mva_per_capita_index_2015"]
    frame = pd.DataFrame({
        "year": overlap.astype(int),
        "world_bank_industry_pc_index_2015": wb.loc[overlap].to_numpy(),
        "unido_iip_pc_index_2015": iip.loc[overlap].to_numpy(),
        "unido_mva_pc_index_2015": mva.reindex(overlap).to_numpy(),
    }).set_index("year")
    frame["index_difference_pct"] = 100.0 * (
        frame["unido_iip_pc_index_2015"] / frame["world_bank_industry_pc_index_2015"] - 1.0
    )
    growth = np.log(frame[["world_bank_industry_pc_index_2015", "unido_iip_pc_index_2015"]]).diff().dropna()
    mva_growth = np.log(
        frame[["unido_mva_pc_index_2015", "unido_iip_pc_index_2015"]]
    ).diff().dropna()
    return frame.reset_index(), {
        "proxy_overlap_start": int(frame.index.min()),
        "proxy_overlap_end": int(frame.index.max()),
        "proxy_overlap_count": int(len(frame)),
        "annual_log_growth_correlation": float(growth.corr().iloc[0, 1]),
        "annual_log_growth_correlation_with_unido_mva": float(
            mva_growth.corr().iloc[0, 1]
        ),
        "mean_absolute_index_difference_pct": float(frame["index_difference_pct"].abs().mean()),
        "latest_index_difference_pct": float(frame.iloc[-1]["index_difference_pct"]),
    }


def pooled(frame: pd.DataFrame) -> float:
    return float(np.sqrt(np.average(np.square(frame["log_rmse"]), weights=frame["n"])))


def production_medoid(candidates, indicators: list[Indicator]) -> tuple[int, list[int]]:
    cutoff = max(int(item.observed.index.max()) for item in indicators)
    ranking = add_plausibility_columns(
        select_candidates(candidates, indicators, cutoff, IIP_PRODUCTION_SEGMENTS),
        candidates,
        indicators,
    )
    eligible = ranking.loc[
        ranking["mapping_boundary_count"].eq(0)
        & ranking["plausibility_violation_count"].eq(0)
    ]
    if len(eligible) < 12:
        raise RuntimeError("IIP refit has fewer than 12 admissible candidates")
    ids = [int(value) for value in eligible.head(12)["candidate_id"]]
    ensemble = [candidates[value] for value in ids]
    scales = {item.key: {} for item in indicators}
    for candidate in ensemble:
        _, _, mapped, _ = score_candidate(candidate, indicators, cutoff)
        for key, value in mapped.items():
            scales[key][candidate.candidate_id] = value
    central, _ = select_medoid(ensemble, indicators, scales)
    return central, ids


def production_comparison(candidates, current: list[Indicator], alternative: list[Indicator]):
    current_id = int(json.loads((HYBRID / "manifest.json").read_text())["central_candidate_id"])
    alternative_id, ensemble = production_medoid(candidates, alternative)
    bridged = apply_observation_bridges(candidates)
    predictions = {}
    for name, candidate_id, indicators in (
        ("current_world_bank", current_id, current),
        ("unido_iip_audit", alternative_id, alternative),
    ):
        candidate = bridged[candidate_id]
        cutoff = max(int(item.observed.index.max()) for item in indicators)
        _, _, scales, _ = score_candidate(candidate, indicators, cutoff)
        predictions[name] = {
            item.key: scales[item.key] * candidate.simulation[item.key] for item in indicators
        }
    rows = []
    for year in (2030, 2035):
        for indicator in (item.key for item in current):
            baseline = float(predictions["current_world_bank"][indicator].loc[year])
            audit = float(predictions["unido_iip_audit"][indicator].loc[year])
            rows.append({"year": year, "indicator": indicator, "current_world_bank": baseline,
                         "unido_iip_audit": audit, "change_pct": 100.0 * (audit / baseline - 1.0)})
    return pd.DataFrame(rows), current_id, alternative_id, ensemble


def main() -> None:
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    current, _ = build_indicators()
    alternative = replace_industry(current, iip_per_capita())
    candidates = load_candidates_fast(parameter_candidates())
    observed, statistics = observed_comparison(current, alternative)
    proxy, nonindustry = backtests(candidates, current, alternative)
    production, current_id, alternative_id, ensemble = production_comparison(candidates, current, alternative)

    temporal = proxy.loc[
        proxy["origin"].eq(TEMPORAL_COMPARISON_ORIGIN)
        & proxy["evaluation_proxy"].eq("unido_iip_volume")
    ].set_index("selector_proxy")
    improvement = 100.0 * (
        temporal.loc["world_bank_industry", "log_rmse"]
        - temporal.loc["unido_iip_volume", "log_rmse"]
    ) / temporal.loc["world_bank_industry", "log_rmse"]

    nonindustry = nonindustry.loc[nonindustry["origin"].eq(TEMPORAL_COMPARISON_ORIGIN)]
    baseline = nonindustry.loc[nonindustry["selector_proxy"].eq("world_bank_industry")]
    audit = nonindustry.loc[nonindustry["selector_proxy"].eq("unido_iip_volume")]
    pooled_worsening = 100.0 * (pooled(audit) / pooled(baseline) - 1.0)
    sectors = baseline.set_index("indicator")[["log_rmse"]].join(
        audit.set_index("indicator")[["log_rmse"]], lsuffix="_baseline", rsuffix="_iip"
    )
    sectors["worsening_pct"] = 100.0 * (
        sectors["log_rmse_iip"] / sectors["log_rmse_baseline"] - 1.0
    )
    maximum_sector_worsening = float(max(0.0, sectors["worsening_pct"].max()))
    coverage = float(provenance["mva_2020_weight_coverage_pct"])
    accepted = bool(
        coverage >= MINIMUM_MVA_WEIGHT_COVERAGE_PCT
        and improvement >= MINIMUM_IIP_IMPROVEMENT_PCT
        and pooled_worsening <= MAXIMUM_NONINDUSTRY_POOLED_WORSENING_PCT
        and maximum_sector_worsening <= MAXIMUM_NONINDUSTRY_SECTOR_WORSENING_PCT
    )
    reasons = []
    if coverage < MINIMUM_MVA_WEIGHT_COVERAGE_PCT:
        reasons.append("balanced-panel 2020 MVA coverage below 90%")
    if improvement < MINIMUM_IIP_IMPROVEMENT_PCT:
        reasons.append("IIP industry improvement below 5%")
    if pooled_worsening > MAXIMUM_NONINDUSTRY_POOLED_WORSENING_PCT:
        reasons.append("pooled non-industry worsening above 5%")
    if maximum_sector_worsening > MAXIMUM_NONINDUSTRY_SECTOR_WORSENING_PCT:
        reasons.append("a non-industry sector worsened by more than 10%")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    observed.to_csv(OUTPUT / "observed_proxy_comparison.csv", index=False)
    proxy.to_csv(OUTPUT / "cross_proxy_backtest.csv", index=False)
    nonindustry.to_csv(OUTPUT / "temporal_nonindustry_backtest.csv", index=False)
    sectors.reset_index().to_csv(OUTPUT / "temporal_nonindustry_comparison.csv", index=False)
    production.to_csv(OUTPUT / "production_projection_comparison.csv", index=False)
    manifest = {
        "audit": "UNIDO real manufacturing IIP as industrial target",
        "status": "accepted_as_future_refit_candidate" if accepted else "accepted_as_independent_diagnostic_only",
        "data_decision": "add_to_observed_data_registry_as_independent_real_output_benchmark",
        "calibration_decision": "eligible_for_controlled_future_joint_refit" if accepted else "do_not_change_BAU_Hybrid_2026_v0.10.0",
        "central_projection_changed": False,
        "public_reconstruction_not_official_world_aggregate": True,
        "observation_start": int(iip_per_capita().index.min()),
        "observation_end": int(iip_per_capita().index.max()),
        "observation_count": int(len(iip_per_capita())),
        **statistics,
        "balanced_country_count": int(provenance["balanced_country_count"]),
        "mva_2020_weight_coverage_pct": coverage,
        "origins": list(ORIGINS),
        "unavailable_standard_origin": 2009,
        "unavailable_standard_origin_reason": (
            "The balanced public IIP panel starts in 2005 and therefore does not "
            "provide the minimum calibration overlap required at origin 2009."
        ),
        "temporal_comparison_origin": TEMPORAL_COMPARISON_ORIGIN,
        "temporal_comparison_reused_across_project_audits": True,
        "iip_industry_improvement_pct": float(improvement),
        "nonindustry_pooled_worsening_pct": float(pooled_worsening),
        "maximum_nonindustry_sector_worsening_pct": maximum_sector_worsening,
        "acceptance_rule": {
            "minimum_iip_improvement_pct": MINIMUM_IIP_IMPROVEMENT_PCT,
            "maximum_nonindustry_pooled_worsening_pct": MAXIMUM_NONINDUSTRY_POOLED_WORSENING_PCT,
            "maximum_nonindustry_sector_worsening_pct": MAXIMUM_NONINDUSTRY_SECTOR_WORSENING_PCT,
            "minimum_mva_weight_coverage_pct": MINIMUM_MVA_WEIGHT_COVERAGE_PCT,
        },
        "calibration_promotion_rejection_reasons": reasons,
        "current_central_candidate_id": current_id,
        "iip_central_candidate_id": alternative_id,
        "iip_ensemble_candidate_ids": ensemble,
        "interpretation_limit": provenance["interpretation_limit"],
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(proxy.to_string(index=False), flush=True)
    print(production.to_string(index=False), flush=True)
    print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
