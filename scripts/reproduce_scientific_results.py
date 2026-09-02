#!/usr/bin/env python3
"""Rebuild the frozen scientific release and compare it with packaged app data.

CSV and JSON structure is compared exactly. Floating-point values are compared with a
very small tolerance because mathematically equivalent BLAS/libm implementations can
legitimately differ in their final machine-precision digits across CI platforms.
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT / "science"
OUTPUT = SCIENCE / "outputs" / "joint_hybrid_2026"
PACKAGED = ROOT / "data" / "scenarios"
FILES = [
    "population.csv",
    "industry_per_capita.csv",
    "food_per_capita.csv",
    "pollution_pressure.csv",
    "human_welfare.csv",
    "industry_total.csv",
    "persistent_pollution_stock.csv",
    "resources_remaining_pct.csv",
    "backtest_2019_latest.csv",
    "backtest_multi_origin.csv",
    "fit_diagnostics.csv",
    "parameter_identifiability.csv",
    "candidate_ranking.csv",
    "validation_candidate_ranking.csv",
    "bridge_validation.csv",
    "lookup_extrapolation_audit.csv",
]

RELATIVE_TOLERANCE = Decimal("1e-12")
ABSOLUTE_TOLERANCE = Decimal("1e-12")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inputs() -> None:
    manifest_path = SCIENCE / "data" / "input_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest["files"].items():
        path = ROOT / relative
        if sha256(path) != expected:
            raise RuntimeError(f"Scientific input hash mismatch: {relative}")
    for relative, metadata in manifest.get("remote_files", {}).items():
        path = ROOT / relative
        if (
            not path.is_file()
            or path.stat().st_size != int(metadata["size_bytes"])
            or sha256(path) != metadata["sha256"]
        ):
            raise RuntimeError(f"Remote scientific input hash mismatch: {relative}")


def run(script: str) -> None:
    environment = os.environ.copy()
    paths = [str(SCIENCE / "src"), str(SCIENCE / "scripts"), str(SCIENCE / "vendor")]
    if environment.get("PYTHONPATH"):
        paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    subprocess.run(
        [sys.executable, str(SCIENCE / "scripts" / script)],
        cwd=SCIENCE,
        env=environment,
        check=True,
    )


def decimal_value(value: str) -> Decimal | None:
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def numeric_difference(
    generated: Decimal,
    packaged: Decimal,
    location: str,
) -> Decimal:
    difference = abs(generated - packaged)
    allowed = max(
        ABSOLUTE_TOLERANCE,
        RELATIVE_TOLERANCE * max(abs(generated), abs(packaged)),
    )
    if difference > allowed:
        raise RuntimeError(
            f"Reproduction mismatch at {location}: generated={generated}, "
            f"packaged={packaged}, absolute difference={difference}, "
            f"allowed={allowed}"
        )
    return difference


def compare_csv(generated: Path, packaged: Path) -> Decimal:
    with generated.open(newline="", encoding="utf-8") as generated_handle:
        generated_rows = list(csv.reader(generated_handle))
    with packaged.open(newline="", encoding="utf-8") as packaged_handle:
        packaged_rows = list(csv.reader(packaged_handle))

    if len(generated_rows) != len(packaged_rows):
        raise RuntimeError(
            f"Reproduction mismatch in {generated.name}: generated row count "
            f"{len(generated_rows)} != packaged row count {len(packaged_rows)}"
        )

    maximum_difference = Decimal(0)
    for row_number, (generated_row, packaged_row) in enumerate(
        zip(generated_rows, packaged_rows), start=1
    ):
        if len(generated_row) != len(packaged_row):
            raise RuntimeError(
                f"Reproduction mismatch in {generated.name}, row {row_number}: "
                f"generated column count {len(generated_row)} != packaged column "
                f"count {len(packaged_row)}"
            )
        for column_number, (generated_cell, packaged_cell) in enumerate(
            zip(generated_row, packaged_row), start=1
        ):
            if generated_cell == packaged_cell:
                continue
            generated_number = decimal_value(generated_cell)
            packaged_number = decimal_value(packaged_cell)
            if generated_number is None or packaged_number is None:
                raise RuntimeError(
                    f"Reproduction mismatch in {generated.name}, row {row_number}, "
                    f"column {column_number}: {generated_cell!r} != {packaged_cell!r}"
                )
            difference = numeric_difference(
                generated_number,
                packaged_number,
                f"{generated.name}, row {row_number}, column {column_number}",
            )
            maximum_difference = max(maximum_difference, difference)
    return maximum_difference


def compare_json_values(generated, packaged, location: str) -> Decimal:
    if isinstance(generated, dict) and isinstance(packaged, dict):
        if generated.keys() != packaged.keys():
            raise RuntimeError(f"Reproduction mismatch at {location}: JSON keys differ")
        maximum = Decimal(0)
        for key in generated:
            maximum = max(
                maximum,
                compare_json_values(generated[key], packaged[key], f"{location}.{key}"),
            )
        return maximum
    if isinstance(generated, list) and isinstance(packaged, list):
        if len(generated) != len(packaged):
            raise RuntimeError(f"Reproduction mismatch at {location}: list lengths differ")
        maximum = Decimal(0)
        for index, (generated_item, packaged_item) in enumerate(zip(generated, packaged)):
            maximum = max(
                maximum,
                compare_json_values(
                    generated_item, packaged_item, f"{location}[{index}]"
                ),
            )
        return maximum
    if type(generated) is not type(packaged):
        raise RuntimeError(
            f"Reproduction mismatch at {location}: JSON types "
            f"{type(generated).__name__} and {type(packaged).__name__} differ"
        )
    if isinstance(generated, Decimal):
        return numeric_difference(generated, packaged, location)
    if generated != packaged:
        raise RuntimeError(
            f"Reproduction mismatch at {location}: {generated!r} != {packaged!r}"
        )
    return Decimal(0)


def compare_json(generated: Path, packaged: Path) -> Decimal:
    generated_payload = json.loads(
        generated.read_text(encoding="utf-8"), parse_float=Decimal
    )
    packaged_payload = json.loads(
        packaged.read_text(encoding="utf-8"), parse_float=Decimal
    )
    return compare_json_values(generated_payload, packaged_payload, generated.name)


def compare(generated: Path, packaged: Path) -> Decimal:
    if generated.read_bytes() == packaged.read_bytes():
        return Decimal(0)
    if generated.suffix == ".csv":
        return compare_csv(generated, packaged)
    if generated.suffix == ".json":
        return compare_json(generated, packaged)
    raise RuntimeError(f"No semantic comparator for {generated.name}")


def main() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "fetch_science_inputs.py")],
        cwd=ROOT,
        check=True,
    )
    verify_inputs()
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    run("run_world3_03.py")
    run("build_joint_hybrid_2026.py")
    maximum_difference = Decimal(0)
    for filename in FILES:
        maximum_difference = max(
            maximum_difference,
            compare(OUTPUT / filename, PACKAGED / filename),
        )
    maximum_difference = max(
        maximum_difference,
        compare(OUTPUT / "manifest.json", PACKAGED / "bau_hybrid_2026_manifest.json"),
    )
    print(
        f"Reproducere științifică reușită: {len(FILES)} CSV-uri și manifest "
        f"semantic identice; abatere numerică absolută maximă "
        f"{maximum_difference}."
    )


if __name__ == "__main__":
    main()
