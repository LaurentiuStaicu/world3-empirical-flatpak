"""Build a frozen public-data world IIP diagnostic with 2020 MVA weights."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

import pandas as pd

from world3_empirical.sources.unido_iip import (
    ACTIVITY_CODE,
    BASE_YEAR,
    DATASET_KEY,
    VARIABLE_CODE,
    WEIGHT_VARIABLE,
    aggregate_balanced_panel,
    parse_iip_export,
    parse_metadata,
    parse_mva_weights,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DATE = date(2026, 9, 8)
RAW = ROOT / "data" / "raw" / "unido" / SNAPSHOT_DATE.isoformat()
PROCESSED = ROOT / "data" / "processed"
OUTPUT = PROCESSED / "unido_iip_world_public_2026-09-08.csv"
PROVENANCE = OUTPUT.with_suffix(".provenance.json")
EMPIRICAL = PROCESSED / "empirical_model_inputs_2026-08-28.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    paths = {
        "iip_metadata": RAW / "iip_metadata.json",
        "iip_annual": RAW / "iip_annual_data.csv",
        "iip_country": RAW / "iip_country.csv",
        "iip_metadata_country": RAW / "iip_metadata_country.csv",
        "national_accounts_metadata": RAW / "national_accounts_metadata.json",
        "national_accounts_2020": RAW / "national_accounts_2020_data.csv",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Frozen UNIDO source files are missing: {missing}")

    metadata = parse_metadata(paths["iip_metadata"].read_bytes())
    iip = parse_iip_export(pd.read_csv(paths["iip_annual"]))
    weights = parse_mva_weights(pd.read_csv(paths["national_accounts_2020"]))
    aggregate, diagnostics = aggregate_balanced_panel(iip, weights)

    empirical = pd.read_csv(EMPIRICAL).set_index("year")
    population = empirical["population"].reindex(aggregate["year"]).to_numpy(dtype=float)
    aggregate["population"] = population
    aggregate["manufacturing_iip_per_capita_raw"] = (
        aggregate["manufacturing_iip_2020_100"] / aggregate["population"]
    )
    base = float(
        aggregate.loc[
            aggregate["year"].eq(2015), "manufacturing_iip_per_capita_raw"
        ].iloc[0]
    )
    aggregate["manufacturing_iip_per_capita_index_2015"] = (
        100.0 * aggregate["manufacturing_iip_per_capita_raw"] / base
    )
    aggregate.drop(columns="manufacturing_iip_per_capita_raw").to_csv(
        OUTPUT, index=False, float_format="%.12g"
    )

    provenance = {
        "retrieved_on": SNAPSHOT_DATE.isoformat(),
        "source_institution": "United Nations Industrial Development Organization (UNIDO)",
        "dataset_key": DATASET_KEY,
        "dataset_id_at_retrieval": int(metadata["id"]),
        "dataset_name": metadata["name"],
        "production_year": str(metadata.get("production_year", "")),
        "portal_inserted_on": str(metadata.get("dat_ins", "")),
        "variable_code": VARIABLE_CODE,
        "activity_code": ACTIVITY_CODE,
        "weight_variable": WEIGHT_VARIABLE,
        "weight_base_year": BASE_YEAR,
        "aggregation_method": (
            "Laspeyres-style fixed 2020 MVA weighted mean over countries with a "
            "complete public annual IIP series for 2005-2025"
        ),
        **diagnostics,
        "raw_sha256": {name: sha256(path) for name, path in paths.items()},
        "source_url": "https://stat.unido.org/portal/dataset/getDataset/IIP",
        "methodology_url": (
            "https://stat.unido.org/portal/storage/file/publications/qiip/"
            "iip_method_note_edition2026.pdf"
        ),
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "attribution": "UNIDO Statistics Portal, Index of Industrial Production",
        "interpretation_limit": (
            "This is a reproducible public-data reconstruction, not UNIDO's official "
            "world aggregate. UNIDO does not publish its country-level imputations. "
            "The series covers manufacturing gross output, not construction, mining, "
            "utilities or every component of World3 industrial output."
        ),
    }
    PROVENANCE.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(provenance, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
