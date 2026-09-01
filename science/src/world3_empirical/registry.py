"""Validation for the empirical-series registry."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .scenarios import project_root


REQUIRED_COLUMNS = {
    "series_id",
    "model_variable",
    "concept",
    "source_institution",
    "dataset",
    "source_url",
    "unit",
    "start_year",
    "end_year",
    "frequency",
    "observation_type",
    "status",
    "notes",
}
OBSERVATION_TYPES = {"empirical", "latent", "scenario_only"}


def load_registry(path: str | Path | None = None) -> pd.DataFrame:
    source = Path(path) if path else project_root() / "data" / "registry.csv"
    registry = pd.read_csv(source)
    missing = REQUIRED_COLUMNS - set(registry.columns)
    if missing:
        raise ValueError(f"Registry is missing required columns: {sorted(missing)}")
    if registry["series_id"].duplicated().any():
        duplicates = registry.loc[registry["series_id"].duplicated(), "series_id"].tolist()
        raise ValueError(f"Duplicate series_id values: {duplicates}")
    invalid_types = set(registry["observation_type"]) - OBSERVATION_TYPES
    if invalid_types:
        raise ValueError(f"Invalid observation_type values: {sorted(invalid_types)}")
    invalid_years = registry["end_year"] < registry["start_year"]
    if invalid_years.any():
        ids = registry.loc[invalid_years, "series_id"].tolist()
        raise ValueError(f"end_year precedes start_year for: {ids}")
    return registry

