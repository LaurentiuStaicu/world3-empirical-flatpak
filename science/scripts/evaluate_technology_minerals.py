"""Audit technology-mineral observations against the current World3 projection.

This is deliberately a measurement audit, not a refit. Mine production is an
observed flow, while World3's nonrenewable-resource variable is a latent stock.
The audit quantifies co-movement and concentration without conflating them.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "data" / "processed" / "technology_mineral_production_2026-09-08.csv"
RISK = ROOT / "data" / "processed" / "technology_mineral_risk_2026-09-08.csv"
PROVENANCE = PRODUCTION.with_suffix(".provenance.json")
SCENARIOS = ROOT.parent / "data" / "scenarios"
OUTPUT = ROOT / "outputs" / "technology_minerals"


def log_growth(series: pd.Series) -> pd.Series:
    return np.log(series.astype(float)).diff().dropna()


def paired_correlation(left: pd.Series, right: pd.Series) -> tuple[int, float]:
    frame = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
    return len(frame), float(frame.corr().iloc[0, 1])


def diagnostics(production: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    industry = pd.read_csv(SCENARIOS / "industry_total.csv").set_index("year")
    resources = pd.read_csv(SCENARIOS / "resources_remaining_pct.csv").set_index("year")
    industry_growth = log_growth(industry["observed"])
    resource_use = -resources["hybrid_2026"].diff()
    resource_use_growth = log_growth(resource_use.where(resource_use > 0))
    rows = []
    wide = production.pivot(index="year", columns="commodity", values="production_index_2015_100")
    for commodity in wide:
        series = wide[commodity].dropna()
        growth = log_growth(series)
        industry_n, industry_corr = paired_correlation(growth, industry_growth)
        resource_n, resource_corr = paired_correlation(growth, resource_use_growth)
        rows.append({
            "commodity": commodity,
            "observation_start": int(series.index.min()),
            "observation_end": int(series.index.max()),
            "observation_count": int(len(series)),
            "production_index_2015": float(series.loc[2015]),
            "production_index_2025": float(series.loc[2025]),
            "production_change_2015_2025_pct": float(series.loc[2025] - 100.0),
            "industry_growth_overlap_n": industry_n,
            "annual_log_growth_correlation_with_observed_industry": industry_corr,
            "world3_resource_flow_overlap_n": resource_n,
            "annual_log_growth_correlation_with_world3_resource_use_flow": resource_corr,
        })
    commodity = pd.DataFrame(rows)

    common = wide.dropna().loc[2000:2025]
    portfolio = np.exp(np.log(common).mean(axis=1))
    portfolio.name = "equal_weight_geometric_mean_index_2015_100"
    portfolio = 100.0 * portfolio / float(portfolio.loc[2015])
    portfolio_frame = portfolio.to_frame()
    portfolio_frame["observed_industry_index_2015_100"] = industry["observed"].reindex(portfolio.index)
    portfolio_frame["world3_hybrid_resource_use_flow"] = resource_use.reindex(portfolio.index)
    return commodity, portfolio_frame.reset_index()


def main() -> None:
    production = pd.read_csv(PRODUCTION)
    risk = pd.read_csv(RISK)
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    commodity, portfolio = diagnostics(production)
    p = portfolio.set_index("year")
    n, portfolio_industry_corr = paired_correlation(
        log_growth(p["equal_weight_geometric_mean_index_2015_100"]),
        log_growth(p["observed_industry_index_2015_100"]),
    )
    _, portfolio_resource_corr = paired_correlation(
        log_growth(p["equal_weight_geometric_mean_index_2015_100"]),
        log_growth(p["world3_hybrid_resource_use_flow"].where(p["world3_hybrid_resource_use_flow"] > 0)),
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    commodity.to_csv(OUTPUT / "commodity_diagnostics.csv", index=False)
    portfolio.to_csv(OUTPUT / "equal_weight_portfolio_diagnostic.csv", index=False)
    risk.to_csv(OUTPUT / "mineral_supply_risk_2025.csv", index=False)
    manifest = {
        "audit": "technology-mineral extraction flow and supply concentration",
        "version": "2026-09-08",
        "status": "accepted_as_observed_risk_registry_not_central_calibration",
        "central_projection_changed": False,
        "commodities": sorted(production["commodity"].unique()),
        "latest_observation_year": 2025,
        "latest_values_are_estimates": True,
        "portfolio_overlap_start": int(p.index.min()),
        "portfolio_overlap_end": int(p.index.max()),
        "portfolio_growth_overlap_n": n,
        "portfolio_growth_correlation_with_observed_industry": portfolio_industry_corr,
        "portfolio_growth_correlation_with_world3_resource_use_flow": portfolio_resource_corr,
        "portfolio_interpretation": (
            "Equal-weight geometric mean for sensitivity only; it is not a physical "
            "tonnage total and is not used as a calibration target."
        ),
        "risk_summary": {
            row["commodity"]: {
                "production_cagr_2020_2025_pct": float(row["production_cagr_2020_2025_pct"]),
                "production_hhi_lower_bound": float(row["production_hhi_lower_bound"]),
                "production_hhi_upper_bound": float(row["production_hhi_upper_bound"]),
                "largest_named_producer": row["largest_named_producer"],
                "largest_named_producer_share_pct": float(row["largest_named_producer_share_pct"]),
                "reserve_status": row["reserve_status"],
            }
            for row in risk.to_dict("records")
        },
        "central_rejection_reasons": [
            "mine production is a flow but World3 nonrenewable resources is a latent aggregate stock",
            "tonnes of different commodities are not additive and equal weighting is arbitrary",
            "reported reserves are economic and revisable rather than a fixed geological stock",
            "ore grades, recovery, recycling, refining, inventories, project capacity and substitution are not yet observed jointly",
            "USGS labels the 2025 world production endpoints as estimates",
        ],
        "next_dynamic_states": [
            "mine production capacity by commodity",
            "economically recoverable reserves with vintage",
            "in-use material stock",
            "secondary supply and recycling capacity",
            "refining capacity and geographic concentration",
            "project pipeline with construction and permitting delays",
        ],
        "provenance": provenance,
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(commodity.to_string(index=False))
    print(risk.to_string(index=False))
    print(json.dumps({k: manifest[k] for k in (
        "status", "portfolio_growth_correlation_with_observed_industry",
        "portfolio_growth_correlation_with_world3_resource_use_flow",
    )}, indent=2))


if __name__ == "__main__":
    main()
