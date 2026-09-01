"""Extract a reproducible global energy snapshot from the EI 2026 narrow CSV.

The Energy Institute workbook is the authority.  The input can be the official
download or a byte-for-byte/faithful public mirror; provenance and SHA-256 are
recorded so that the transport copy is never confused with an independent
source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed" / "energy_institute_global_2026.csv"
PROVENANCE = ROOT / "data" / "processed" / "energy_institute_global_2026.provenance.json"

VARIABLES = {
    "tes_ej": "total_primary_energy_ej",
    "oil_tes_ej": "oil_ej",
    "gas_tes_ej": "gas_ej",
    "coal_tes_ej": "coal_ej",
    "nuclear_tes_ej": "nuclear_ej",
    "hydro_tes_ej": "hydro_ej",
    "renewables_tes_ej": "renewables_ej",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract(input_path: Path) -> pd.DataFrame:
    raw = pd.read_csv(input_path, usecols=["Country", "Year", "Var", "Value"])
    selected = raw[
        (raw["Country"] == "Total World") & raw["Var"].isin(VARIABLES)
    ].copy()
    if selected.duplicated(["Year", "Var"]).any():
        raise ValueError("duplicate Total World year-variable observations")

    wide = selected.pivot(index="Year", columns="Var", values="Value")
    missing = set(VARIABLES) - set(wide.columns)
    if missing:
        raise ValueError(f"missing required EI variables: {sorted(missing)}")
    wide = wide.rename(columns=VARIABLES).sort_index()
    if int(wide.index.min()) != 1965 or int(wide.index.max()) != 2025:
        raise ValueError("expected an Energy Institute 2026 series covering 1965-2025")
    if wide.isna().any().any():
        raise ValueError("unexpected gaps in required global EI series")

    wide["fossil_energy_ej"] = wide[["oil_ej", "gas_ej", "coal_ej"]].sum(axis=1)
    wide["fossil_share"] = wide["fossil_energy_ej"] / wide["total_primary_energy_ej"]
    wide["non_fossil_energy_ej"] = (
        wide["total_primary_energy_ej"] - wide["fossil_energy_ej"]
    )
    wide["non_fossil_share"] = 1.0 - wide["fossil_share"]

    component_sum = wide[
        ["oil_ej", "gas_ej", "coal_ej", "nuclear_ej", "hydro_ej", "renewables_ej"]
    ].sum(axis=1)
    wide["component_reconciliation_error_ej"] = (
        component_sum - wide["total_primary_energy_ej"]
    )
    relative_error = (
        wide["component_reconciliation_error_ej"].abs()
        / wide["total_primary_energy_ej"]
    )
    # The EI narrow file contains a small 2019-2023 discrepancy between TES
    # and the displayed fuel components (maximum below 0.1%). Preserve it as
    # data rather than silently forcing the parts to the published total.
    if relative_error.max() > 0.001:
        raise ValueError("EI source components differ from total primary energy by >0.1%")
    if not wide["fossil_share"].between(0, 1).all():
        raise ValueError("invalid fossil share")

    return wide.reset_index()[
        [
            "Year",
            "total_primary_energy_ej",
            "fossil_energy_ej",
            "oil_ej",
            "gas_ej",
            "coal_ej",
            "nuclear_ej",
            "hydro_ej",
            "renewables_ej",
            "non_fossil_energy_ej",
            "fossil_share",
            "non_fossil_share",
            "component_reconciliation_error_ej",
        ]
    ].rename(columns={"Year": "year"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument(
        "--mirror-url",
        default="https://github.com/shanewhi/world-energy-data",
        help="Transport location used for this copy, if not the EI download itself.",
    )
    parser.add_argument("--mirror-commit", default="")
    args = parser.parse_args()

    source = args.input_csv.resolve()
    frame = extract(source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False, float_format="%.10g")

    record = {
        "authority": "Energy Institute",
        "dataset": "Statistical Review of World Energy 2026",
        "official_url": "https://www.energyinst.org/statistical-review/resources-and-data-downloads",
        "transport_url": args.mirror_url,
        "transport_commit": args.mirror_commit or None,
        "input_filename": source.name,
        "input_sha256": sha256(source),
        "input_size_bytes": source.stat().st_size,
        "coverage": {"start_year": 1965, "end_year": 2025},
        "geography": "Total World",
        "output": str(OUTPUT.relative_to(ROOT)),
        "boundary_note": (
            "These are gross primary-energy supply observations. They constrain the "
            "energy mix but do not directly observe EROI or net energy."
        ),
    }
    PROVENANCE.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    latest = frame.iloc[-1]
    print(
        f"Wrote {len(frame)} years; 2025 TES={latest.total_primary_energy_ej:.3f} EJ, "
        f"fossil share={latest.fossil_share:.6%}."
    )


if __name__ == "__main__":
    main()
