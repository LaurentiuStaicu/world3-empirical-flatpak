"""Scenario definitions with explicit evidence labels."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Scenario:
    name: str
    label: str
    evidence_status: str
    description: str
    constant_overrides: Mapping[str, float]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_scenarios(path: str | Path | None = None) -> dict[str, Scenario]:
    source = Path(path) if path else project_root() / "configs" / "scenarios.json"
    with source.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return {
        name: Scenario(name=name, **definition)
        for name, definition in payload.items()
    }

