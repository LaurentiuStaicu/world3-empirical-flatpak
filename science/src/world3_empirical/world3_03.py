"""Adapter for the official Vensim World3-03 scenarios model.

The authoritative ``.mdl`` file is preserved byte-for-byte in ``vendor``.
PySD 3.14 cannot parse one Vensim-only help-link directive, so translation is
performed from a temporary copy with only that non-equation directive removed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Sequence

import numpy as np
import pandas as pd

from .scenarios import project_root


WORLD3_03_OUTPUTS = {
    "population": "population",
    "industrial_output": "industrial_output",
    "industrial_output_per_capita": "industrial_output_per_capita",
    "food": "food",
    "food_per_capita": "food_per_capita",
    "services_per_capita": "service_output_per_capita",
    "nonrenewable_resources": "nonrenewable_resources",
    "nonrenewable_resource_fraction": "fraction_of_resources_remaining",
    "persistent_pollution": "persistent_pollution",
    "persistent_pollution_index": "persistent_pollution_index",
    "persistent_pollution_generation_rate": "persistent_pollution_generation_rate",
    "life_expectancy": "life_expectancy",
    "human_welfare_index": "human_welfare_index",
    "human_ecological_footprint": "human_ecological_footprint",
}

SCENARIO_NAMES = {1: "world3_03_bau", 2: "world3_03_bau2"}


@dataclass(frozen=True)
class World303Result:
    scenario_number: int
    scenario_name: str
    frame: pd.DataFrame

    def peak_year(self, variable: str, start_year: int = 1900) -> float:
        subset = self.frame.loc[self.frame["year"] >= start_year]
        if variable not in subset:
            raise KeyError(f"Unknown output variable: {variable}")
        return float(subset.loc[subset[variable].idxmax(), "year"])


def _source_model_path() -> Path:
    return project_root() / "vendor" / "world3_03" / "World3_03_Scenarios.mdl"


def _sanitized_model_text(source: Path) -> str:
    text = source.read_text(encoding="utf-8-sig")
    directive = (
        "help link :is: 'https://www.vensim.com/documentation/sample_models.html'\n"
        "\t~\tdmnl\n"
        "\t~\t|\n"
    )
    normalized = text.replace("\r\n", "\n")
    if directive not in normalized:
        raise RuntimeError("Expected Vensim help-link directive was not found")
    return normalized.replace(directive, "", 1)


def _import_pysd():
    try:
        import pysd
    except ImportError as exc:
        raise RuntimeError(
            "World3-03 requires the optional dependencies: "
            "pip install -e '.[world3-03]'"
        ) from exc

    if int(np.__version__.split(".", 1)[0]) >= 2:
        raise RuntimeError(
            "PySD 3.14.3 lookup evaluation requires NumPy <2 for this model. "
            "Install the pinned optional dependency group '.[world3-03]'."
        )
    return pysd


def run_world3_03(
    scenario: int = 2,
    *,
    years: Sequence[int] = tuple(range(1900, 2101)),
) -> World303Result:
    """Run the verified official BAU (1) or BAU2 (2) World3-03 scenario."""

    if scenario not in SCENARIO_NAMES:
        raise ValueError(f"Supported World3-03 scenarios: {sorted(SCENARIO_NAMES)}")
    requested_years = np.asarray(tuple(years), dtype=float)
    if requested_years.ndim != 1 or requested_years.size == 0:
        raise ValueError("years must be a non-empty one-dimensional sequence")
    if requested_years.min() < 1900 or requested_years.max() > 2100:
        raise ValueError("The official model time range is 1900-2100")

    pysd = _import_pysd()
    source = _source_model_path()
    with tempfile.TemporaryDirectory(prefix="world3_03_") as directory:
        temporary_model = Path(directory) / source.name
        temporary_model.write_text(_sanitized_model_text(source), encoding="utf-8")
        model = pysd.read_vensim(temporary_model)
        raw = model.run(
            params={"scenario": scenario},
            return_columns=list(WORLD3_03_OUTPUTS.values()),
            return_timestamps=requested_years,
        )

    frame = raw.rename(columns={engine: name for name, engine in WORLD3_03_OUTPUTS.items()})
    frame.index.name = "year"
    frame = frame.reset_index()
    frame["year"] = frame["year"].astype(float)
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise RuntimeError("World3-03 simulation produced non-finite output")
    return World303Result(scenario, SCENARIO_NAMES[scenario], frame)
