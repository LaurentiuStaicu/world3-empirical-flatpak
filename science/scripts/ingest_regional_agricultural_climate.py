"""Build a country-year cereal-production and climate panel.

FAOSTAT M49 country codes are converted to ISO3 codes.  Regional aggregates
do not have ISO country records and are therefore excluded instead of being
silently double counted with their member countries.
"""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import zipfile

import pandas as pd
import pycountry


ROOT = Path(__file__).resolve().parents[1]
RAW_FAO = (
    ROOT
    / "data"
    / "raw"
    / "faostat"
    / "Production_Crops_Livestock_E_All_Data_Normalized_2025.zip"
)
RAW_TEMPERATURE = (
    ROOT
    / "data"
    / "raw"
    / "regional_climate"
    / "annual-temperature-anomalies_2026-08-31.csv"
)
RAW_PRECIPITATION = (
    ROOT
    / "data"
    / "raw"
    / "regional_climate"
    / "global-precipitation-anomaly_2026-08-31.csv"
)
OUTPUT = ROOT / "data" / "processed" / "regional_cereal_climate_panel_2026.csv"
PROVENANCE = (
    ROOT
    / "data"
    / "processed"
    / "regional_cereal_climate_panel_2026.provenance.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iso3_from_m49(value: object) -> str | None:
    numeric = str(value).replace("'", "").strip()
    if not numeric.isdigit():
        return None
    country = pycountry.countries.get(numeric=numeric.zfill(3))
    return None if country is None else country.alpha_3


def load_cereal_production() -> tuple[pd.DataFrame, pd.Series]:
    country_parts: list[pd.DataFrame] = []
    world_parts: list[pd.DataFrame] = []
    with zipfile.ZipFile(RAW_FAO) as archive:
        source = next(
            name
            for name in archive.namelist()
            if name.endswith("All_Data_(Normalized).csv")
        )
        with archive.open(source) as handle:
            for chunk in pd.read_csv(
                handle,
                encoding="latin-1",
                usecols=["Area Code (M49)", "Area", "Item", "Element", "Year", "Unit", "Value"],
                chunksize=300_000,
            ):
                selected = chunk.loc[
                    chunk["Item"].eq("Cereals, primary")
                    & chunk["Element"].eq("Production")
                    & chunk["Unit"].eq("t")
                ].copy()
                if selected.empty:
                    continue
                world = selected.loc[selected["Area"].eq("World"), ["Year", "Value"]]
                if not world.empty:
                    world_parts.append(world)
                selected["code"] = selected["Area Code (M49)"].map(iso3_from_m49)
                country = selected.loc[
                    selected["code"].notna(), ["code", "Area", "Year", "Value"]
                ].rename(
                    columns={
                        "Area": "faostat_area",
                        "Year": "year",
                        "Value": "cereal_production_tonnes",
                    }
                )
                if not country.empty:
                    country_parts.append(country)
    countries = pd.concat(country_parts, ignore_index=True)
    countries = (
        countries.groupby(["code", "faostat_area", "year"], as_index=False)[
            "cereal_production_tonnes"
        ]
        .sum()
        .sort_values(["code", "year"])
    )
    world = (
        pd.concat(world_parts, ignore_index=True)
        .groupby("Year")["Value"]
        .sum()
        .sort_index()
    )
    return countries, world


def main() -> None:
    production, world = load_cereal_production()
    temperature = pd.read_csv(RAW_TEMPERATURE).rename(
        columns={
            "Entity": "entity",
            "Code": "code",
            "Year": "year",
            "Temperature anomaly": "temperature_anomaly_c_1991_2020",
        }
    )
    precipitation = pd.read_csv(RAW_PRECIPITATION).rename(
        columns={
            "Entity": "entity",
            "Code": "code",
            "Year": "year",
            "Annual precipitation anomaly": "precipitation_anomaly_mm_1991_2020",
        }
    )
    # OWID also publishes regional aggregates in the same files.  They have
    # no ISO3 code and must be removed before enforcing country-year keys.
    temperature = temperature.loc[
        temperature["code"].fillna("").str.len().eq(3)
    ].copy()
    precipitation = precipitation.loc[
        precipitation["code"].fillna("").str.len().eq(3)
    ].copy()
    climate = temperature.merge(
        precipitation[["code", "year", "precipitation_anomaly_mm_1991_2020"]],
        on=["code", "year"],
        how="inner",
        validate="one_to_one",
    )
    panel = production.merge(
        climate,
        on=["code", "year"],
        how="inner",
        validate="many_to_one",
    )
    panel = panel[
        [
            "code",
            "entity",
            "faostat_area",
            "year",
            "cereal_production_tonnes",
            "temperature_anomaly_c_1991_2020",
            "precipitation_anomaly_mm_1991_2020",
        ]
    ].sort_values(["code", "year"])
    if panel.duplicated(["code", "year"]).any():
        raise ValueError("Country-year rows must be unique")

    mapped_coverage = (
        panel.groupby("year")["cereal_production_tonnes"].sum() / world
    ).dropna()
    transition_coverage = mapped_coverage.loc[mapped_coverage.index >= 1990]
    stable_coverage = mapped_coverage.loc[mapped_coverage.index >= 1992]
    if float(stable_coverage.min()) < 0.90:
        raise ValueError(
            "Mapped country production covers less than 90% of World cereals "
            "after the 1990-1991 post-Soviet code transition"
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUTPUT, index=False, float_format="%.8g")
    metadata = {
        "created_on": str(date.today()),
        "panel_coverage": {
            "start_year": int(panel.year.min()),
            "end_year": int(panel.year.max()),
            "countries": int(panel.code.nunique()),
        },
        "production_selection": (
            "FAOSTAT Crops and livestock products; Cereals, primary; Production; tonnes"
        ),
        "country_mapping": (
            "FAOSTAT M49 numeric codes to ISO 3166-1 alpha-3 via pycountry; "
            "non-country regional aggregates are excluded"
        ),
        "world_production_coverage": {
            "minimum_1990_latest": float(transition_coverage.min()),
            "minimum_1992_latest": float(stable_coverage.min()),
            "median_1992_latest": float(stable_coverage.median()),
            "method_note": (
                "1990-1991 are retained but excluded from the >=90% gate because "
                "the USSR and successor-state code transition is not representable "
                "as a one-to-one current ISO3 country mapping"
            ),
        },
        "climate_source": (
            "Contains modified Copernicus Climate Change Service ERA5 information, "
            "processed by Our World in Data"
        ),
        "raw_files": {
            str(RAW_FAO.relative_to(ROOT)): sha256(RAW_FAO),
            str(RAW_TEMPERATURE.relative_to(ROOT)): sha256(RAW_TEMPERATURE),
            str(RAW_PRECIPITATION.relative_to(ROOT)): sha256(RAW_PRECIPITATION),
        },
        "source_urls": {
            "faostat": (
                "https://bulks-faostat.fao.org/production/"
                "Production_Crops_Livestock_E_All_Data_(Normalized).zip"
            ),
            "temperature": (
                "https://ourworldindata.org/grapher/"
                "annual-temperature-anomalies.csv"
            ),
            "precipitation": (
                "https://ourworldindata.org/grapher/"
                "global-precipitation-anomaly.csv"
            ),
        },
        "important_limit": (
            "Annual country means do not represent crop calendars, subnational "
            "extremes, irrigation, soil moisture or crop-specific thresholds."
        ),
    }
    PROVENANCE.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(panel.tail().to_string(index=False))
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
