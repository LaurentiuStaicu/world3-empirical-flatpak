"""Auditable adapter for the UNIDO Statistics Portal National Accounts API."""

from __future__ import annotations

import json
from typing import Any, Iterable
import urllib.request

import pandas as pd


API_ROOT = "https://stat.unido.org/portal/dataset"
DATASET_KEY = "NATIONAL_ACCOUNTS"
WORLD_GROUP = "WORLD"
DEFAULT_VARIABLES = ("MvaCod", "Pop")


def metadata_url(dataset_key: str = DATASET_KEY) -> str:
    return f"{API_ROOT}/getDataset/{dataset_key}"


def data_url() -> str:
    return f"{API_ROOT}/getDataWithoutActivities"


def parse_metadata(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    metadata = json.loads(raw) if isinstance(raw, (bytes, str)) else raw
    required = {"id", "name", "countries", "groups", "periods", "variables"}
    if not isinstance(metadata, dict) or not required.issubset(metadata):
        raise ValueError("Unexpected UNIDO National Accounts metadata response")
    if not any(group.get("c") == WORLD_GROUP for group in metadata["groups"]):
        raise ValueError("UNIDO metadata does not contain the WORLD aggregate")
    available = {variable.get("c") for variable in metadata["variables"]}
    missing = set(DEFAULT_VARIABLES) - available
    if missing:
        raise ValueError(f"UNIDO metadata is missing variables: {sorted(missing)}")
    return metadata


def request_payload(
    metadata: dict[str, Any],
    *,
    country_code: str = WORLD_GROUP,
    variables: Iterable[str] = DEFAULT_VARIABLES,
) -> dict[str, Any]:
    """Build a request without hard-coding UNIDO's dynamic dataset identifier."""

    periods = [str(period) for period in metadata["periods"]]
    if not periods:
        raise ValueError("UNIDO metadata contains no periods")
    return {
        "datasetId": int(metadata["id"]),
        "countryCode": country_code,
        "fullPrecision": True,
        "variableCodes": list(variables),
        "periods": periods,
    }


def parse_data(
    raw: bytes | str | dict[str, Any],
    *,
    country_code: str = WORLD_GROUP,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    payload = json.loads(raw) if isinstance(raw, (bytes, str)) else raw
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Unexpected UNIDO National Accounts data response")
    records = []
    for row in payload["data"]:
        if row.get("p") is None or row.get("c") is None or row.get("v") is None:
            continue
        records.append(
            {
                "year": int(row["p"]),
                "indicator": str(row["c"]),
                "value": float(row["v"]),
                "country_code": country_code,
            }
        )
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        raise ValueError("UNIDO returned no observations")
    duplicates = frame.duplicated(["year", "indicator"])
    if duplicates.any():
        raise ValueError("UNIDO returned duplicate year-variable observations")
    found = set(frame["indicator"])
    missing = set(DEFAULT_VARIABLES) - found
    if missing:
        raise ValueError(f"UNIDO response is missing variables: {sorted(missing)}")
    metadata = payload.get("ym", [])
    if not isinstance(metadata, list):
        raise ValueError("Unexpected UNIDO year-metadata response")
    return frame.sort_values(["year", "indicator"]).reset_index(drop=True), metadata


def fetch_national_accounts(timeout: int = 90) -> tuple[bytes, bytes]:
    headers = {"User-Agent": "World3-Empirical-reproducibility/0.10.2"}
    request = urllib.request.Request(metadata_url(), headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw_metadata = response.read()
    metadata = parse_metadata(raw_metadata)
    body = json.dumps(request_payload(metadata)).encode("utf-8")
    request = urllib.request.Request(
        data_url(),
        data=body,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw_data = response.read()
    parse_data(raw_data)
    return raw_metadata, raw_data
