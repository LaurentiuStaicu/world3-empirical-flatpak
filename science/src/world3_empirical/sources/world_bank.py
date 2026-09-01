"""Small, auditable World Bank API adapter using only the standard library."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
import urllib.parse
import urllib.request

import pandas as pd


API_ROOT = "https://api.worldbank.org/v2"


@dataclass(frozen=True)
class WorldBankSeries:
    indicator: str
    model_variable: str
    concept: str
    unit: str


def build_url(indicator: str, country: str = "WLD") -> str:
    safe_country = urllib.parse.quote(country, safe="")
    safe_indicator = urllib.parse.quote(indicator, safe=".")
    return f"{API_ROOT}/country/{safe_country}/indicator/{safe_indicator}?format=json&per_page=20000"


def fetch_world_bank_series(indicator: str, country: str = "WLD", timeout: int = 30) -> tuple[bytes, pd.DataFrame]:
    request = urllib.request.Request(build_url(indicator, country), headers={"User-Agent": "world3-empirical-2026/0.2"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return raw, parse_world_bank_payload(raw, indicator)


def parse_world_bank_payload(raw: bytes | str | list[Any], indicator: str) -> pd.DataFrame:
    payload = json.loads(raw) if isinstance(raw, (bytes, str)) else raw
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ValueError(f"Unexpected World Bank response for {indicator}")
    records = []
    for row in payload[1]:
        value = row.get("value")
        year = row.get("date")
        if value is None or year is None:
            continue
        records.append(
            {
                "year": int(year),
                "value": float(value),
                "indicator": indicator,
                "country_code": row.get("countryiso3code", "WLD"),
            }
        )
    if not records:
        raise ValueError(f"World Bank returned no observations for {indicator}")
    return pd.DataFrame.from_records(records).sort_values("year").reset_index(drop=True)

