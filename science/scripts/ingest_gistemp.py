"""Create a versioned global annual-temperature snapshot from NASA GISTEMP v4."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "climate" / "GISTEMP_v4_2026-08-31.csv"
OUTPUT = ROOT / "data" / "processed" / "nasa_gistemp_global_2026.csv"
PROVENANCE = ROOT / "data" / "processed" / "nasa_gistemp_global_2026.provenance.json"
SOURCE_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    frame = pd.read_csv(RAW, skiprows=1, na_values=["***"])
    frame["Year"] = pd.to_numeric(frame["Year"], errors="coerce")
    frame["J-D"] = pd.to_numeric(frame["J-D"], errors="coerce")
    annual = frame.loc[frame["Year"].notna() & frame["J-D"].notna(), ["Year", "J-D"]]
    annual = annual.rename(
        columns={"Year": "year", "J-D": "temperature_anomaly_c_1951_1980"}
    )
    annual["year"] = annual["year"].astype(int)
    annual = annual.loc[annual["year"].le(2025)].sort_values("year")
    if annual["year"].duplicated().any():
        raise ValueError("GISTEMP annual years must be unique")
    if (int(annual.year.min()), int(annual.year.max())) != (1880, 2025):
        raise ValueError("Expected complete annual GISTEMP coverage for 1880-2025")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    annual.to_csv(OUTPUT, index=False, float_format="%.4f")
    metadata = {
        "institution": "NASA Goddard Institute for Space Studies",
        "dataset": "GISTEMP v4 Land-Ocean Temperature Index",
        "source_url": SOURCE_URL,
        "accessed_on": str(date.today()),
        "raw_file": str(RAW.relative_to(ROOT)),
        "raw_sha256": sha256(RAW),
        "coverage": {"start_year": 1880, "end_year": 2025},
        "selection": "Global annual J-D Land-Ocean Temperature Index",
        "unit": "degrees Celsius relative to the 1951-1980 mean",
        "revision_note": (
            "GISTEMP is revised when late station and ocean observations arrive; "
            "the hash fixes the exact snapshot used by this audit."
        ),
    }
    PROVENANCE.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(annual.tail().to_string(index=False))
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
