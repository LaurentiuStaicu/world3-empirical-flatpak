"""Source-faithful parsing for global technology-mineral production.

The historical input is the OWID adaptation of USGS/BGS global series.  The
2024 and 2025 endpoints are replaced by the newer USGS MCS 2026 data release.
Commodities remain separate because their reported tonnes are not additive.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


OWID_VALUE = "Global mine production of different minerals"
COMMODITIES = {
    "Copper": "copper",
    "Nickel": "nickel",
    "Lithium": "lithium",
    "Cobalt": "cobalt",
    "Rare earths": "rare_earths",
    "Graphite": "graphite",
}
USGS_COMMODITIES = {
    "Copper": "copper",
    "Nickel": "nickel",
    "Lithium": "lithium",
    "Cobalt": "cobalt",
    "Rare Earths": "rare_earths",
    "Graphite (Natural)": "graphite",
}


def parse_owid_history(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Entity", "Year", OWID_VALUE}
    if not required.issubset(frame.columns):
        raise ValueError(f"OWID mineral input is missing columns: {sorted(required - set(frame.columns))}")
    selected = frame.loc[frame["Entity"].isin(COMMODITIES)].copy()
    selected["commodity"] = selected["Entity"].map(COMMODITIES)
    selected["year"] = pd.to_numeric(selected["Year"], errors="raise").astype(int)
    selected["production_tonnes"] = pd.to_numeric(selected[OWID_VALUE], errors="raise")
    selected = selected[["commodity", "year", "production_tonnes"]]
    if selected.empty or (selected["production_tonnes"] <= 0).any():
        raise ValueError("OWID mineral input has no usable positive selected observations")
    if selected.duplicated(["commodity", "year"]).any():
        raise ValueError("OWID mineral input has duplicate commodity-year rows")
    return selected.sort_values(["commodity", "year"]).reset_index(drop=True)


def _numeric_value(value: object) -> tuple[float, bool] | None:
    if pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "—", "--", "NA", "W", "s"}:
        return None
    lower_bound = text.startswith(">")
    text = re.sub(r"^[><]", "", text)
    try:
        return float(text), lower_bound
    except ValueError as error:
        raise ValueError(f"Unrecognized USGS numeric cell: {value!r}") from error


def parse_usgs_mcs(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "Commodity", "Country", "Statistics", "Statistics_detail",
        "Unit", "Year", "Value", "Notes",
    }
    if not required.issubset(frame.columns):
        raise ValueError(f"USGS MCS input is missing columns: {sorted(required - set(frame.columns))}")
    selected = frame.loc[
        frame["Commodity"].isin(USGS_COMMODITIES)
        & frame["Statistics"].isin(["Production", "Reserves"])
        & pd.to_numeric(frame["Year"], errors="coerce").isin([2024, 2025])
    ].copy()
    selected["commodity"] = selected["Commodity"].map(USGS_COMMODITIES)
    selected["year"] = pd.to_numeric(selected["Year"], errors="raise").astype(int)
    parsed = selected["Value"].map(_numeric_value)
    selected["value"] = parsed.map(lambda item: np.nan if item is None else item[0])
    selected["lower_bound"] = parsed.map(lambda item: False if item is None else item[1])
    multiplier = selected["Unit"].map({"metric tons": 1.0, "thousand metric tons": 1000.0})
    if multiplier.isna().any():
        raise ValueError("USGS MCS input contains an unsupported unit")
    selected["value_tonnes"] = selected["value"] * multiplier
    selected["estimated"] = selected["Notes"].fillna("").str.contains("Estimated", case=False)
    result = selected[[
        "commodity", "Country", "Statistics", "Statistics_detail", "year",
        "value_tonnes", "lower_bound", "estimated", "Notes",
    ]].rename(columns={
        "Country": "country",
        "Statistics": "statistic",
        "Statistics_detail": "statistic_detail",
        "Notes": "notes",
    })
    return result.sort_values(["commodity", "statistic", "country", "year"]).reset_index(drop=True)


def stitch_latest_production(history: pd.DataFrame, mcs: pd.DataFrame) -> pd.DataFrame:
    latest = mcs.loc[
        mcs["statistic"].eq("Production")
        & mcs["statistic_detail"].str.startswith("Mine production")
        & mcs["country"].eq("World total")
        & mcs["year"].isin([2024, 2025])
    ].copy()
    if latest.duplicated(["commodity", "year"]).any() or len(latest) != 12:
        raise ValueError("Expected one USGS world mine-production row per commodity and year")
    prior = history.loc[history["year"] < 2024].copy()
    prior["source_vintage"] = "OWID USGS/BGS harmonization, updated 2025-12-15"
    prior["estimated"] = False
    current = latest[["commodity", "year", "value_tonnes", "estimated"]].rename(
        columns={"value_tonnes": "production_tonnes"}
    )
    current["source_vintage"] = "USGS Mineral Commodity Summaries 2026 data release"
    result = pd.concat([prior, current], ignore_index=True)
    result = result.sort_values(["commodity", "year"]).reset_index(drop=True)
    if result.duplicated(["commodity", "year"]).any():
        raise ValueError("Stitched mineral series has duplicate commodity-year rows")
    bases = result.loc[result["year"].eq(2015)].set_index("commodity")["production_tonnes"]
    if set(bases.index) != set(COMMODITIES.values()):
        raise ValueError("Every selected commodity requires a 2015 normalization value")
    result["production_index_2015_100"] = 100.0 * result["production_tonnes"] / result["commodity"].map(bases)
    return result


def build_2025_risk_table(production: pd.DataFrame, mcs: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for commodity in sorted(COMMODITIES.values()):
        world = float(
            production.loc[
                production["commodity"].eq(commodity) & production["year"].eq(2025),
                "production_tonnes",
            ].iloc[0]
        )
        country_rows = mcs.loc[
            mcs["commodity"].eq(commodity)
            & mcs["year"].eq(2025)
            & mcs["statistic"].eq("Production")
            & mcs["statistic_detail"].str.startswith("Mine production")
            & ~mcs["country"].isin(["World total", "Other countries"])
            & mcs["value_tonnes"].notna()
        ].copy()
        shares = country_rows["value_tonnes"] / world
        residual_share = max(0.0, 1.0 - float(shares.sum()))
        hhi_lower = float(np.square(shares).sum())
        hhi_upper = hhi_lower + residual_share**2
        leader_index = country_rows["value_tonnes"].idxmax()
        reserve = mcs.loc[
            mcs["commodity"].eq(commodity)
            & mcs["year"].eq(2025)
            & mcs["statistic"].eq("Reserves")
            & mcs["country"].eq("World total")
        ]
        if len(reserve) != 1:
            raise ValueError(f"Expected one world reserve row for {commodity}")
        reserve_value = float(reserve.iloc[0]["value_tonnes"])
        reserve_lower_bound = bool(reserve.iloc[0]["lower_bound"])
        reserve_status = "reported_lower_bound" if reserve_lower_bound else "reported"
        # The current MCS 2026 v1.3 PDF revised rare-earth reserves from the
        # data-release value (>85 Mt) to >75 Mt.  Exclude the stale ratio rather
        # than silently mixing vintages.
        if commodity == "rare_earths":
            reserve_value = np.nan
            reserve_status = "excluded_data_release_vs_report_v1_3_conflict"
        output_2020 = float(
            production.loc[
                production["commodity"].eq(commodity) & production["year"].eq(2020),
                "production_tonnes",
            ].iloc[0]
        )
        rows.append({
            "commodity": commodity,
            "production_2025_tonnes": world,
            "production_2025_estimated": bool(
                production.loc[
                    production["commodity"].eq(commodity) & production["year"].eq(2025),
                    "estimated",
                ].iloc[0]
            ),
            "production_cagr_2020_2025_pct": 100.0 * ((world / output_2020) ** (1.0 / 5.0) - 1.0),
            "named_country_coverage_pct": 100.0 * float(shares.sum()),
            "production_hhi_lower_bound": hhi_lower,
            "production_hhi_upper_bound": hhi_upper,
            "largest_named_producer": str(country_rows.loc[leader_index, "country"]),
            "largest_named_producer_share_pct": 100.0 * float(shares.loc[leader_index]),
            "reported_reserves_2025_tonnes": reserve_value,
            "reserve_status": reserve_status,
            "reserve_to_annual_output_ratio": reserve_value / world,
        })
    return pd.DataFrame(rows)
