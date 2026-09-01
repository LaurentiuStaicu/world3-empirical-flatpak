"""Ingest the published global fossil-fuel EROI series (1971-2020)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed" / "aramendia_global_fossil_eroi_2024.csv"
PROVENANCE = OUTPUT.with_suffix(".provenance.json")
EXPECTED_MD5 = "c3f330ee874e10aca547d73d76cd3cd2"
STAGES = {
    "Primary": "primary",
    "Final (fuel+elec+heat)": "final",
    "Useful (fuel+elec+heat)": "useful",
}


def md5(path: Path) -> str:
    digest = hashlib.md5()  # nosec: checksum published by Figshare, not security
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract(path: Path) -> pd.DataFrame:
    actual_md5 = md5(path)
    if actual_md5 != EXPECTED_MD5:
        raise ValueError(f"Figshare MD5 mismatch: {actual_md5}")
    raw = pd.read_csv(path)
    selected = raw[
        raw["Country"].eq("WRLD")
        & raw["Product.Group"].eq("All fossil fuels")
        & raw["Energy.stage"].isin(STAGES)
    ]
    years = [str(year) for year in range(1971, 2021)]
    records = {"year": list(range(1971, 2021))}
    for stage, short_name in STAGES.items():
        for indirect in ("Included", "Excluded"):
            row = selected[
                selected["Energy.stage"].eq(stage)
                & selected["Indirect.Energy"].eq(indirect)
            ]
            if len(row) != 1:
                raise ValueError(f"expected one row for {stage}, {indirect}")
            suffix = "including_indirect" if indirect == "Included" else "direct_only"
            records[f"fossil_{short_name}_eroi_{suffix}"] = (
                row.iloc[0][years].astype(float).to_list()
            )
    frame = pd.DataFrame(records)
    if not (frame.drop(columns="year") > 1).all().all():
        raise ValueError("EROI must remain above one")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    args = parser.parse_args()
    source = args.input_csv.resolve()
    frame = extract(source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False, float_format="%.10g")
    provenance = {
        "authors": "Aramendia et al.",
        "publication_year": 2024,
        "article_doi": "10.1038/s41560-024-01518-6",
        "dataset_doi": "10.6084/m9.figshare.25311358",
        "figshare_file_id": 46240243,
        "figshare_filename": "global_erois.csv",
        "input_md5": md5(source),
        "coverage": {"start_year": 1971, "end_year": 2020},
        "selection": "WRLD; All fossil fuels; primary/final/useful; indirect included/excluded",
        "boundary_note": (
            "Primary, final and useful EROI are different accounting boundaries and "
            "must never be pooled into one calibration target."
        ),
    }
    PROVENANCE.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(frame)} years; 2020 primary/final/useful EROI="
        f"{frame.iloc[-1].fossil_primary_eroi_including_indirect:.3f}/"
        f"{frame.iloc[-1].fossil_final_eroi_including_indirect:.3f}/"
        f"{frame.iloc[-1].fossil_useful_eroi_including_indirect:.3f}."
    )


if __name__ == "__main__":
    main()
