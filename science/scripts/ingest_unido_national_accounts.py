"""Create a frozen world-manufacturing snapshot from the UNIDO portal API."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

import pandas as pd

from world3_empirical.sources.unido import (
    DATASET_KEY,
    WORLD_GROUP,
    data_url,
    fetch_national_accounts,
    metadata_url,
    parse_data,
    parse_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DATE = date(2026, 9, 7)
RAW = ROOT / "data" / "raw" / "unido" / SNAPSHOT_DATE.isoformat()
PROCESSED = ROOT / "data" / "processed"
OUTPUT = PROCESSED / "unido_national_accounts_world_2026-09-07.csv"
PROVENANCE = OUTPUT.with_suffix(".provenance.json")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    metadata_path = RAW / "national_accounts_metadata.json"
    data_path = RAW / "national_accounts_world.json"
    if metadata_path.is_file() and data_path.is_file():
        raw_metadata = metadata_path.read_bytes()
        raw_data = data_path.read_bytes()
    else:
        raw_metadata, raw_data = fetch_national_accounts()
        metadata_path.write_bytes(raw_metadata)
        data_path.write_bytes(raw_data)

    metadata = parse_metadata(raw_metadata)
    observations, year_metadata = parse_data(raw_data)
    wide = observations.pivot(index="year", columns="indicator", values="value")
    required = wide[["MvaCod", "Pop"]].dropna().copy()
    required.columns = ["mva_constant_2020_usd", "population"]
    required["mva_per_capita_constant_2020_usd"] = (
        required["mva_constant_2020_usd"] / required["population"]
    )
    required["mva_per_capita_index_2015"] = (
        100.0
        * required["mva_per_capita_constant_2020_usd"]
        / float(required.loc[2015, "mva_per_capita_constant_2020_usd"])
    )
    required.reset_index().to_csv(OUTPUT, index=False, float_format="%.12g")

    variable_metadata = {
        variable["c"]: variable for variable in metadata["variables"]
        if variable.get("c") in {"MvaCod", "Pop"}
    }
    provenance = {
        "retrieved_on": SNAPSHOT_DATE.isoformat(),
        "source_institution": "United Nations Industrial Development Organization (UNIDO)",
        "dataset_key": DATASET_KEY,
        "dataset_id_at_retrieval": int(metadata["id"]),
        "dataset_name": metadata["name"],
        "production_year": str(metadata.get("production_year", "")),
        "portal_inserted_on": str(metadata.get("dat_ins", "")),
        "aggregation": WORLD_GROUP,
        "variables": variable_metadata,
        "period_start": int(required.index.min()),
        "period_end": int(required.index.max()),
        "observations": int(len(required)),
        "year_metadata": year_metadata,
        "metadata_url": metadata_url(),
        "data_url": data_url(),
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "attribution": "UNIDO Statistics Portal, National Accounts Database",
        "raw_metadata_sha256": sha256(raw_metadata),
        "raw_data_sha256": sha256(raw_data),
        "unit_note": (
            "The portal variable label says constant 2020 USD while its base_year "
            "field reports 2015. The snapshot preserves the published label and "
            "records this metadata inconsistency rather than silently resolving it."
        ),
        "use_limit": (
            "MVA is conceptually closer to manufacturing than the current World Bank "
            "industry-including-construction proxy, but it remains value added rather "
            "than the physical gross output represented by World3."
        ),
    }
    PROVENANCE.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(provenance, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
