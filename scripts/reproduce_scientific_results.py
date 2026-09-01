#!/usr/bin/env python3
"""Rebuild the frozen scientific release and compare it byte-for-byte with app data."""

from __future__ import annotations

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


def compare(generated: Path, packaged: Path) -> None:
    if generated.read_bytes() != packaged.read_bytes():
        raise RuntimeError(
            f"Reproduction mismatch: {generated.relative_to(ROOT)} differs from "
            f"{packaged.relative_to(ROOT)}"
        )


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
    for filename in FILES:
        compare(OUTPUT / filename, PACKAGED / filename)
    compare(OUTPUT / "manifest.json", PACKAGED / "bau_hybrid_2026_manifest.json")
    print(f"Reproducere științifică reușită: {len(FILES)} CSV-uri și manifest identice byte-for-byte.")


if __name__ == "__main__":
    main()
