"""Build a frozen global technology-mineral production and risk snapshot."""

from __future__ import annotations

import hashlib
import json
import gzip
from pathlib import Path

import pandas as pd

from world3_empirical.sources.minerals import (
    build_2025_risk_table,
    parse_owid_history,
    parse_usgs_mcs,
    stitch_latest_production,
)


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "minerals" / "2026-09-08"
OWID = RAW / "owid_global_mine_production.csv"
OWID_METADATA = RAW / "owid_global_mine_production.metadata.json"
MCS = RAW / "MCS2026_Commodities_Data.normalized-lf.csv.gz"
PRODUCTION = ROOT / "data" / "processed" / "technology_mineral_production_2026-09-08.csv"
RISK = ROOT / "data" / "processed" / "technology_mineral_risk_2026-09-08.csv"
PROVENANCE = ROOT / "data" / "processed" / "technology_mineral_production_2026-09-08.provenance.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decompressed_sha256(path: Path) -> str:
    return hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()


def main() -> None:
    history = parse_owid_history(pd.read_csv(OWID))
    mcs = parse_usgs_mcs(pd.read_csv(MCS, encoding="cp1252", dtype=str))
    production = stitch_latest_production(history, mcs)
    risk = build_2025_risk_table(production, mcs)
    production.to_csv(PRODUCTION, index=False)
    risk.to_csv(RISK, index=False)
    metadata = json.loads(OWID_METADATA.read_text(encoding="utf-8"))
    payload = {
        "snapshot_date": "2026-09-08",
        "commodities": sorted(production["commodity"].unique()),
        "historical_observation_range": [int(production["year"].min()), 2023],
        "current_endpoint_range": [2024, 2025],
        "historical_source": metadata["chart"]["citation"],
        "historical_source_url": "https://ourworldindata.org/grapher/global-mine-production-minerals",
        "historical_source_sha256": sha256(OWID),
        "historical_processing": (
            "OWID prioritizes USGS and supplements with BGS; 2024 is replaced "
            "by the newer MCS 2026 vintage together with the 2025 estimate."
        ),
        "current_source": "USGS Mineral Commodity Summaries 2026 data release",
        "current_source_doi": "10.5066/P1WKQ63T",
        "current_report_doi": "10.3133/mcs2026",
        "current_source_archive_sha256": sha256(MCS),
        "current_source_normalized_lf_sha256": decompressed_sha256(MCS),
        "current_source_official_crlf_md5": "36185ff3742087e1dd90c52fe634fe12",
        "current_source_official_crlf_sha256": "582a0aa231aea53d8a97dc8d1cd3dfa5f885cf3760353e3d029d7f0ae4fbaaf5",
        "line_ending_normalization": (
            "The committed MCS CSV is the official cp1252 file normalized from "
            "CRLF to LF and deterministically gzip-compressed. Decompression and "
            "restoration of CRLF reproduce the recorded official hashes."
        ),
        "endpoint_estimation": "USGS marks the 2025 world mine-production rows as estimated.",
        "aggregation_rule": "No tonnes are summed across commodities; each material remains separate.",
        "hhi_rule": (
            "Lower bound sums squared named-country shares; upper bound treats "
            "all residual world production as one producer."
        ),
        "reserve_limit": (
            "Reserve-to-output is a static diagnostic, not years until depletion. "
            "Reserves change with prices, technology, exploration and reporting."
        ),
        "rare_earth_revision_conflict": (
            "The ScienceBase data release reports >85 Mt of 2025 world reserves, "
            "while the current MCS 2026 v1.3 chapter reports >75 Mt. The risk table "
            "therefore excludes the rare-earth reserve-to-output ratio."
        ),
        "world3_mapping_limit": (
            "Mine production is a flow and cannot directly calibrate World3's "
            "latent aggregate stock of nonrenewable resources."
        ),
    }
    PROVENANCE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(production.groupby("commodity").agg(start=("year", "min"), end=("year", "max"), n=("year", "size")))
    print(risk.to_string(index=False))


if __name__ == "__main__":
    main()
