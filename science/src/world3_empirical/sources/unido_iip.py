"""Parsing and public-data aggregation for UNIDO's 2020-base IIP dataset."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


DATASET_KEY = "IIP"
ACTIVITY_CODE = "C"
VARIABLE_CODE = "52"
WEIGHT_VARIABLE = "MvaCud"
BASE_YEAR = 2020


def parse_metadata(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    metadata = json.loads(raw) if isinstance(raw, (bytes, str)) else raw
    required = {"id", "name", "countries", "periods", "variables"}
    if not isinstance(metadata, dict) or not required.issubset(metadata):
        raise ValueError("Unexpected UNIDO IIP metadata response")
    variables = {str(item.get("c")) for item in metadata["variables"]}
    if VARIABLE_CODE not in variables:
        raise ValueError("UNIDO IIP metadata does not contain the original index")
    return metadata


def parse_iip_export(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Year", "Country", "CountryCode", "VariableCode", "ActivityCode", "Value"}
    if not required.issubset(frame.columns):
        raise ValueError(f"UNIDO IIP export is missing columns: {sorted(required - set(frame.columns))}")
    selected = frame.loc[
        frame["VariableCode"].astype(str).eq(VARIABLE_CODE)
        & frame["ActivityCode"].astype(str).eq(ACTIVITY_CODE),
        ["Year", "Country", "CountryCode", "Value"],
    ].copy()
    selected.columns = ["year", "country", "country_code", "iip"]
    selected["year"] = pd.to_numeric(selected["year"], errors="raise").astype(int)
    selected["country_code"] = pd.to_numeric(selected["country_code"], errors="raise").astype(int)
    selected["iip"] = pd.to_numeric(selected["iip"], errors="raise")
    if selected.empty or (selected["iip"] <= 0).any():
        raise ValueError("UNIDO IIP export contains no usable positive observations")
    if selected.duplicated(["country_code", "year"]).any():
        raise ValueError("UNIDO IIP export contains duplicate country-year observations")
    return selected.sort_values(["country_code", "year"]).reset_index(drop=True)


def parse_mva_weights(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Year", "Country", "CountryCode", "VariableCode", "Value"}
    if not required.issubset(frame.columns):
        raise ValueError(f"UNIDO MVA export is missing columns: {sorted(required - set(frame.columns))}")
    selected = frame.loc[
        frame["VariableCode"].astype(str).eq(WEIGHT_VARIABLE)
        & pd.to_numeric(frame["Year"], errors="coerce").eq(BASE_YEAR),
        ["Country", "CountryCode", "Value"],
    ].copy()
    selected.columns = ["country", "country_code", "mva_current_2020_usd"]
    selected["country_code"] = pd.to_numeric(selected["country_code"], errors="raise").astype(int)
    selected["mva_current_2020_usd"] = pd.to_numeric(
        selected["mva_current_2020_usd"], errors="raise"
    )
    if selected.empty or (selected["mva_current_2020_usd"] <= 0).any():
        raise ValueError("UNIDO MVA export contains no usable positive 2020 weights")
    if selected.duplicated("country_code").any():
        raise ValueError("UNIDO MVA export contains duplicate country weights")
    return selected.sort_values("country_code").reset_index(drop=True)


def aggregate_balanced_panel(
    iip: pd.DataFrame,
    weights: pd.DataFrame,
    *,
    start_year: int = 2005,
    end_year: int = 2025,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Reconstruct a transparent fixed-weight world series from published rows.

    UNIDO's official aggregate additionally uses unpublished imputations.  A
    balanced public panel prevents changing country coverage from masquerading
    as growth while retaining the fixed 2020 MVA weights in the 2026 method.
    """

    years = list(range(start_year, end_year + 1))
    panel = iip.loc[iip["year"].isin(years)].pivot(
        index="country_code", columns="year", values="iip"
    )
    panel = panel.dropna(subset=years)
    weight_series = weights.set_index("country_code")["mva_current_2020_usd"]
    codes = panel.index.intersection(weight_series.index)
    if not len(codes):
        raise ValueError("UNIDO IIP and MVA exports have no common balanced countries")
    panel = panel.loc[codes, years]
    used_weights = weight_series.loc[codes]
    aggregate = panel.mul(used_weights, axis=0).sum(axis=0) / used_weights.sum()
    result = pd.DataFrame({"year": years, "manufacturing_iip_2020_100": aggregate.values})
    total_weight = float(weight_series.sum())
    diagnostics = {
        "panel_start": start_year,
        "panel_end": end_year,
        "balanced_country_count": int(len(codes)),
        "available_weight_country_count": int(len(weight_series)),
        "mva_2020_weight_coverage_pct": float(100.0 * used_weights.sum() / total_weight),
        "included_mva_2020_usd": float(used_weights.sum()),
        "total_available_mva_2020_usd": total_weight,
    }
    return result, diagnostics
