"""Create a dated, reproducible snapshot of selected World Bank indicators."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

import pandas as pd

from world3_empirical.sources.world_bank import (
    WorldBankSeries,
    build_url,
    fetch_world_bank_series,
    parse_world_bank_payload,
)


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "world_bank" / "2026-08-28"
PROCESSED = ROOT / "data" / "processed"

SERIES = [
    WorldBankSeries("SP.POP.TOTL", "population", "Global population", "persons"),
    WorldBankSeries("NV.IND.TOTL.KD", "industrial_output", "Industry value added", "constant 2015 USD"),
    WorldBankSeries("AG.PRD.FOOD.XD", "food_production_index", "Food production index", "2014-2016=100"),
    WorldBankSeries("EN.GHG.CO2.MT.CE.AR5", "fossil_co2_proxy", "Territorial CO2 emissions", "Mt CO2e, AR5"),
]


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    frames = []
    manifest = {"retrieved_on": str(date(2026, 8, 28)), "source": "World Bank API", "series": []}
    for definition in SERIES:
        raw_path = RAW / f"{definition.indicator}.json"
        if raw_path.exists():
            raw = raw_path.read_bytes()
            frame = parse_world_bank_payload(raw, definition.indicator)
        else:
            raw, frame = fetch_world_bank_series(definition.indicator, timeout=15)
            raw_path.write_bytes(raw)
        frame["model_variable"] = definition.model_variable
        frame["concept"] = definition.concept
        frame["unit"] = definition.unit
        frames.append(frame)
        manifest["series"].append(
            {
                "indicator": definition.indicator,
                "url": build_url(definition.indicator),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "first_year": int(frame["year"].min()),
                "last_year": int(frame["year"].max()),
                "observations": int(len(frame)),
            }
        )
    observations = pd.concat(frames, ignore_index=True)
    observations.to_csv(PROCESSED / "world_bank_global_snapshot_2026-08-28.csv", index=False)

    wide = observations.pivot(index="year", columns="model_variable", values="value").sort_index()
    if {"food_production_index", "population"}.issubset(wide.columns):
        base_year = 2015
        per_capita = wide["food_production_index"] / wide["population"]
        wide["food_per_capita_proxy_index"] = 100 * per_capita / per_capita.loc[base_year]
    wide.reset_index().to_csv(PROCESSED / "empirical_model_inputs_2026-08-28.csv", index=False)
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
