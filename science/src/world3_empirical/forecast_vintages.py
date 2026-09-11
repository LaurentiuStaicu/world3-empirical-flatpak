"""External forecasts are benchmarks, never observations for calibration.

Availability is conservatively the capture date: a live page can be corrected
after its nominal release. Earlier availability requires an archived edition.
"""
from datetime import date
import json
import math
from pathlib import Path


def load_forecasts(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload["schema_version"] != "1.0":
        raise ValueError("Unsupported forecast schema")
    records = payload["records"]
    seen = set()
    for row in records:
        if row["evidence_type"] != "forecast":
            raise ValueError("Forecast registry cannot contain observations")
        released = date.fromisoformat(row["release_date"])
        captured = date.fromisoformat(row["captured_on"])
        available = date.fromisoformat(row["available_from"])
        if not released <= available <= captured:
            raise ValueError("Invalid availability chronology")
        if available != captured:
            raise ValueError("This schema requires conservative capture-date availability")
        if type(row["target_year"]) is not int or row["target_year"] < released.year:
            raise ValueError("Invalid forecast target year")
        if isinstance(row["value"], bool) or not isinstance(row["value"], (int, float)) or not math.isfinite(row["value"]) or row["value"] < 0:
            raise ValueError("Invalid forecast value")
        for field in ("provider", "series_id", "geography", "unit", "scenario", "source_url", "source_locator"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise ValueError(f"Missing {field}")
        key = tuple(row[k] for k in ("provider", "series_id", "geography", "unit", "scenario", "release_date", "captured_on", "target_year"))
        if key in seen:
            raise ValueError("Duplicate forecast vintage")
        seen.add(key)
    return records


def available_forecasts(records: list[dict], as_of: date) -> list[dict]:
    """Retain all eligible vintages; never silently select the newest revision."""
    return [dict(row) for row in records if date.fromisoformat(row["available_from"]) <= as_of]


def calibration_observations(records: list[dict]) -> list[dict]:
    """Explicit guard for consumers trying to use this registry as training data."""
    if records:
        raise ValueError("External forecasts must not be used as observed calibration targets")
    return []
