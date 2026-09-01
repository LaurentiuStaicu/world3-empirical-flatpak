#!/usr/bin/env python3
"""Generate non-production scientific audit artifacts required by the full test suite."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT / "science"
SCRIPTS = (
    "build_bau2_e2026.py",
    "evaluate_climate_food_link.py",
    "evaluate_eroi_resource_link.py",
    "evaluate_regional_agricultural_stress.py",
    "analyze_energy_coupling.py",
)


def main() -> None:
    joint = SCIENCE / "outputs" / "joint_hybrid_2026" / "candidate_simulations.npz"
    if not joint.is_file():
        raise RuntimeError(
            "Joint release outputs are missing; run reproduce_scientific_results.py first"
        )
    environment = os.environ.copy()
    python_paths = (
        SCIENCE / "src",
        SCIENCE / "scripts",
        SCIENCE / "vendor",
    )
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        [*(str(path) for path in python_paths), *([existing] if existing else [])]
    )
    for script in SCRIPTS:
        print(f"Generating scientific test artifact: {script}", flush=True)
        subprocess.run(
            [sys.executable, str(SCIENCE / "scripts" / script)],
            cwd=SCIENCE,
            env=environment,
            check=True,
        )


if __name__ == "__main__":
    main()
