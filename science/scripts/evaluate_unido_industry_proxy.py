"""Audit UNIDO manufacturing value added as the industrial observation target.

The production model currently uses World Bank industry value added, including
construction, divided by population.  UNIDO MVA is conceptually narrower and
closer to manufacturing, but it is still value added rather than World3 gross
physical output.  This audit substitutes only the observed industrial series,
keeps the candidate design and all structural equations fixed, and tests the
choice prospectively.  It does not alter the packaged projection.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_bau2_e2026 import Indicator, build_indicators
from build_joint_hybrid_2026 import (
    PRODUCTION_SEGMENTS,
    VALIDATION_SEGMENTS,
    add_plausibility_columns,
    apply_observation_bridges,
    observation_mapping,
    parameter_candidates,
    run_candidates,
    score_candidate,
    select_candidates,
    select_medoid,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "unido_national_accounts_world_2026-09-07.csv"
PROVENANCE = DATA.with_suffix(".provenance.json")
HYBRID = ROOT / "outputs" / "joint_hybrid_2026"
OUTPUT = ROOT / "outputs" / "unido_industry_proxy"
ORIGINS = (2009, 2014, 2018)
DEVELOPMENT_ORIGINS = (2009, 2014)
TEMPORAL_COMPARISON_ORIGIN = 2018
MINIMUM_UNIDO_INDUSTRY_IMPROVEMENT_PCT = 5.0
MAXIMUM_NONINDUSTRY_POOLED_WORSENING_PCT = 5.0
MAXIMUM_NONINDUSTRY_SECTOR_WORSENING_PCT = 10.0


def unido_industry() -> pd.Series:
    frame = pd.read_csv(DATA).set_index("year")
    series = frame["mva_per_capita_constant_2020_usd"].dropna()
    return 100.0 * series / float(series.loc[2015])


def replace_industry(
    indicators: list[Indicator], observed: pd.Series
) -> list[Indicator]:
    replaced = []
    for indicator in indicators:
        if indicator.key != "industry_per_capita":
            replaced.append(indicator)
            continue
        replaced.append(
            replace(
                indicator,
                observed=observed,
                unit="UNIDO MVA pe locuitor, indice 2015=100",
                source="UNIDO National Accounts, WORLD, MvaCod / Pop",
                source_url=(
                    "https://stat.unido.org/portal/dataset/getDataset/"
                    "NATIONAL_ACCOUNTS"
                ),
                status=(
                    "observat/estimat până în 2025; MVA exclude construcțiile, "
                    "dar rămâne valoare adăugată, nu producție fizică brută"
                ),
            )
        )
    return replaced


def selected_id(candidates, indicators: list[Indicator], origin: int) -> int:
    segments = tuple(segment for segment in VALIDATION_SEGMENTS if segment[1] <= origin)
    if not segments:
        raise ValueError(f"No validation segment is available at origin {origin}")
    ranking = select_candidates(candidates, indicators, origin, segments)
    eligible = ranking.loc[ranking["mapping_boundary_count"].eq(0)]
    return int((eligible if not eligible.empty else ranking).iloc[0]["candidate_id"])


def log_rmse(observed: pd.Series, predicted: pd.Series) -> float:
    overlap = observed.index.intersection(predicted.index)
    observed_values = observed.loc[overlap].to_numpy(dtype=float)
    predicted_values = predicted.loc[overlap].to_numpy(dtype=float)
    return float(np.sqrt(np.mean(np.square(np.log(predicted_values / observed_values)))))


def mape(observed: pd.Series, predicted: pd.Series) -> float:
    overlap = observed.index.intersection(predicted.index)
    observed_values = observed.loc[overlap].to_numpy(dtype=float)
    predicted_values = predicted.loc[overlap].to_numpy(dtype=float)
    return float(100.0 * np.mean(np.abs(predicted_values / observed_values - 1.0)))


def forecast(
    candidate,
    indicator: Indicator,
    origin: int,
) -> tuple[pd.Series, pd.Series]:
    observed = indicator.observed.loc[indicator.observed.index > origin].dropna()
    scale, _ = observation_mapping(
        indicator, candidate.simulation[indicator.key], origin
    )
    predicted = scale * candidate.simulation[indicator.key].reindex(observed.index)
    return observed, predicted


def proxy_comparison(
    candidates,
    original: list[Indicator],
    alternative: list[Indicator],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_name = {"world_bank_industry": original, "unido_mva": alternative}
    industry = {
        name: next(item for item in indicators if item.key == "industry_per_capita")
        for name, indicators in by_name.items()
    }
    proxy_rows = []
    system_rows = []
    for origin in ORIGINS:
        ids = {
            name: selected_id(candidates, indicators, origin)
            for name, indicators in by_name.items()
        }
        for selector, candidate_id in ids.items():
            candidate = candidates[candidate_id]
            for evaluation_proxy, indicator in industry.items():
                observed, predicted = forecast(candidate, indicator, origin)
                proxy_rows.append(
                    {
                        "origin": origin,
                        "selector_proxy": selector,
                        "evaluation_proxy": evaluation_proxy,
                        "selected_candidate_id": candidate_id,
                        "evaluation_start": int(observed.index.min()),
                        "evaluation_end": int(observed.index.max()),
                        "n": int(len(observed)),
                        "log_rmse": log_rmse(observed, predicted),
                        "mape_pct": mape(observed, predicted),
                    }
                )
            # Non-industry targets are identical under both proxy definitions.
            for indicator in original:
                if indicator.key == "industry_per_capita":
                    continue
                observed, predicted = forecast(candidate, indicator, origin)
                system_rows.append(
                    {
                        "origin": origin,
                        "selector_proxy": selector,
                        "indicator": indicator.key,
                        "selected_candidate_id": candidate_id,
                        "n": int(len(observed)),
                        "log_rmse": log_rmse(observed, predicted),
                        "mape_pct": mape(observed, predicted),
                    }
                )
    return pd.DataFrame(proxy_rows), pd.DataFrame(system_rows)


def observed_proxy_comparison(
    original: list[Indicator], alternative: list[Indicator]
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    world_bank = next(
        item.observed for item in original if item.key == "industry_per_capita"
    )
    unido = next(
        item.observed for item in alternative if item.key == "industry_per_capita"
    )
    overlap = world_bank.index.intersection(unido.index)
    frame = pd.DataFrame(
        {
            "year": overlap.astype(int),
            "world_bank_industry_pc_index_2015": world_bank.loc[overlap].to_numpy(),
            "unido_mva_pc_index_2015": unido.loc[overlap].to_numpy(),
        }
    ).set_index("year")
    frame["index_difference_pct"] = 100.0 * (
        frame["unido_mva_pc_index_2015"]
        / frame["world_bank_industry_pc_index_2015"]
        - 1.0
    )
    frame["world_bank_log_growth"] = np.log(
        frame["world_bank_industry_pc_index_2015"]
    ).diff()
    frame["unido_log_growth"] = np.log(frame["unido_mva_pc_index_2015"]).diff()
    growth = frame[["world_bank_log_growth", "unido_log_growth"]].dropna()
    statistics = {
        "proxy_overlap_start": int(frame.index.min()),
        "proxy_overlap_end": int(frame.index.max()),
        "proxy_overlap_count": int(len(frame)),
        "annual_log_growth_correlation": float(
            growth["world_bank_log_growth"].corr(growth["unido_log_growth"])
        ),
        "mean_absolute_index_difference_pct": float(
            frame["index_difference_pct"].abs().mean()
        ),
        "latest_index_difference_pct": float(
            frame.loc[frame.index.max(), "index_difference_pct"]
        ),
    }
    return frame.reset_index(), statistics


def pooled(frame: pd.DataFrame) -> float:
    return float(
        np.sqrt(
            np.average(
                np.square(frame["log_rmse"].to_numpy(dtype=float)),
                weights=frame["n"].to_numpy(dtype=float),
            )
        )
    )


def production_medoid(candidates, indicators: list[Indicator]) -> tuple[int, list[int]]:
    cutoff = max(int(indicator.observed.index.max()) for indicator in indicators)
    ranking = select_candidates(candidates, indicators, cutoff, PRODUCTION_SEGMENTS)
    ranking = add_plausibility_columns(ranking, candidates, indicators)
    eligible = ranking.loc[
        ranking["mapping_boundary_count"].eq(0)
        & ranking["plausibility_violation_count"].eq(0)
    ]
    if len(eligible) < 12:
        raise RuntimeError("UNIDO refit has fewer than 12 admissible candidates")
    ensemble_ids = [int(value) for value in eligible.head(12)["candidate_id"]]
    ensemble = [candidates[value] for value in ensemble_ids]
    scales = {indicator.key: {} for indicator in indicators}
    for candidate in ensemble:
        _, _, mapped, _ = score_candidate(candidate, indicators, cutoff)
        for key, value in mapped.items():
            scales[key][candidate.candidate_id] = value
    central_id, _ = select_medoid(ensemble, indicators, scales)
    return central_id, ensemble_ids


def production_comparison(
    candidates,
    original: list[Indicator],
    alternative: list[Indicator],
) -> tuple[pd.DataFrame, dict[str, object]]:
    original_manifest = json.loads((HYBRID / "manifest.json").read_text())
    original_id = int(original_manifest["central_candidate_id"])
    alternative_id, alternative_ensemble = production_medoid(candidates, alternative)
    bridged = apply_observation_bridges(candidates)
    configurations = {
        "current_world_bank": (original_id, original),
        "unido_mva_audit": (alternative_id, alternative),
    }
    predictions: dict[str, dict[str, pd.Series]] = {}
    for name, (candidate_id, indicators) in configurations.items():
        candidate = bridged[candidate_id]
        cutoff = max(int(indicator.observed.index.max()) for indicator in indicators)
        _, _, scales, _ = score_candidate(candidate, indicators, cutoff)
        predictions[name] = {
            indicator.key: scales[indicator.key] * candidate.simulation[indicator.key]
            for indicator in indicators
        }
    rows = []
    for year in (2030, 2035):
        for indicator in (item.key for item in original):
            current = float(predictions["current_world_bank"][indicator].loc[year])
            alternative_value = float(predictions["unido_mva_audit"][indicator].loc[year])
            rows.append(
                {
                    "year": year,
                    "indicator": indicator,
                    "current_world_bank": current,
                    "unido_mva_audit": alternative_value,
                    "change_pct": 100.0 * (alternative_value / current - 1.0),
                }
            )
    return pd.DataFrame(rows), {
        "current_central_candidate_id": original_id,
        "unido_central_candidate_id": alternative_id,
        "unido_ensemble_candidate_ids": alternative_ensemble,
    }


def main() -> None:
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    original, _ = build_indicators()
    alternative = replace_industry(original, unido_industry())
    candidates = run_candidates(parameter_candidates())
    observed_comparison, proxy_statistics = observed_proxy_comparison(
        original, alternative
    )
    proxy, nonindustry = proxy_comparison(candidates, original, alternative)
    production, production_ids = production_comparison(
        candidates, original, alternative
    )

    temporal_proxy = proxy.loc[
        proxy["origin"].eq(TEMPORAL_COMPARISON_ORIGIN)
        & proxy["evaluation_proxy"].eq("unido_mva")
    ].set_index("selector_proxy")
    industry_improvement = 100.0 * (
        temporal_proxy.loc["world_bank_industry", "log_rmse"]
        - temporal_proxy.loc["unido_mva", "log_rmse"]
    ) / temporal_proxy.loc["world_bank_industry", "log_rmse"]

    temporal_nonindustry = nonindustry.loc[
        nonindustry["origin"].eq(TEMPORAL_COMPARISON_ORIGIN)
    ]
    baseline = temporal_nonindustry.loc[
        temporal_nonindustry["selector_proxy"].eq("world_bank_industry")
    ]
    alternative_rows = temporal_nonindustry.loc[
        temporal_nonindustry["selector_proxy"].eq("unido_mva")
    ]
    baseline_pooled = pooled(baseline)
    alternative_pooled = pooled(alternative_rows)
    pooled_worsening = 100.0 * (alternative_pooled - baseline_pooled) / baseline_pooled
    sectors = baseline.set_index("indicator")[["log_rmse"]].join(
        alternative_rows.set_index("indicator")[["log_rmse"]],
        lsuffix="_baseline",
        rsuffix="_unido",
    )
    sectors["worsening_pct"] = 100.0 * (
        sectors["log_rmse_unido"] - sectors["log_rmse_baseline"]
    ) / sectors["log_rmse_baseline"]
    maximum_sector_worsening = float(max(0.0, sectors["worsening_pct"].max()))
    accepted = bool(
        industry_improvement >= MINIMUM_UNIDO_INDUSTRY_IMPROVEMENT_PCT
        and pooled_worsening <= MAXIMUM_NONINDUSTRY_POOLED_WORSENING_PCT
        and maximum_sector_worsening <= MAXIMUM_NONINDUSTRY_SECTOR_WORSENING_PCT
    )

    rejection_reasons = []
    if industry_improvement < MINIMUM_UNIDO_INDUSTRY_IMPROVEMENT_PCT:
        rejection_reasons.append("UNIDO industry improvement below 5%")
    if pooled_worsening > MAXIMUM_NONINDUSTRY_POOLED_WORSENING_PCT:
        rejection_reasons.append("pooled non-industry worsening above 5%")
    if maximum_sector_worsening > MAXIMUM_NONINDUSTRY_SECTOR_WORSENING_PCT:
        rejection_reasons.append("a non-industry sector worsened by more than 10%")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    observed_comparison.to_csv(OUTPUT / "observed_proxy_comparison.csv", index=False)
    proxy.to_csv(OUTPUT / "cross_proxy_backtest.csv", index=False)
    nonindustry.to_csv(OUTPUT / "nonindustry_backtest.csv", index=False)
    sectors.reset_index().to_csv(
        OUTPUT / "temporal_nonindustry_comparison.csv", index=False
    )
    production.to_csv(OUTPUT / "production_projection_comparison.csv", index=False)
    manifest = {
        "audit": "UNIDO WORLD manufacturing value added as industrial target",
        "status": (
            "accepted_as_independent_diagnostic_and_future_refit_candidate"
            if accepted
            else "accepted_as_independent_diagnostic_only"
        ),
        "data_decision": "add_to_observed_data_registry_as_independent_benchmark",
        "calibration_decision": (
            "eligible_for_controlled_future_joint_refit"
            if accepted
            else "do_not_change_BAU_Hybrid_2026_v0.10.0"
        ),
        "central_projection_changed": False,
        "dataset": "UNIDO National Accounts Database",
        "dataset_production_year": provenance["production_year"],
        "portal_inserted_on": provenance["portal_inserted_on"],
        "aggregation": "WORLD",
        "observation_start": int(unido_industry().index.min()),
        "observation_end": int(unido_industry().index.max()),
        "observation_count": int(len(unido_industry())),
        "latest_year_is_unido_estimate": True,
        **proxy_statistics,
        "development_origins": list(DEVELOPMENT_ORIGINS),
        "temporal_comparison_origin": TEMPORAL_COMPARISON_ORIGIN,
        "temporal_comparison_reused_across_project_audits": True,
        "unido_industry_improvement_pct": float(industry_improvement),
        "nonindustry_pooled_worsening_pct": float(pooled_worsening),
        "maximum_nonindustry_sector_worsening_pct": maximum_sector_worsening,
        "acceptance_rule": {
            "minimum_unido_industry_improvement_pct": MINIMUM_UNIDO_INDUSTRY_IMPROVEMENT_PCT,
            "maximum_nonindustry_pooled_worsening_pct": MAXIMUM_NONINDUSTRY_POOLED_WORSENING_PCT,
            "maximum_nonindustry_sector_worsening_pct": MAXIMUM_NONINDUSTRY_SECTOR_WORSENING_PCT,
        },
        "calibration_promotion_rejection_reasons": rejection_reasons,
        **production_ids,
        "interpretation_limit": (
            "UNIDO MVA excludes construction and is a better-defined manufacturing "
            "target, but remains monetary value added rather than World3 gross "
            "physical output. The 2018 comparison is temporally separated but has "
            "been reused in earlier project audits and is not a pristine holdout."
        ),
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(proxy.to_string(index=False), flush=True)
    print(production.to_string(index=False), flush=True)
    print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
