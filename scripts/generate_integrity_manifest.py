#!/usr/bin/env python3
"""Generate the deterministic SHA-256 manifest for packaged scenario data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "data" / "scenarios"
OUTPUT = SCENARIOS / "release_integrity.json"


def app_version() -> str:
    text = (ROOT / "meson.build").read_text(encoding="utf-8")
    match = re.search(r"version:\s*'([^']+)'", text)
    if not match:
        raise RuntimeError("Cannot read application version from meson.build")
    return match.group(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    model = json.loads((SCENARIOS / "bau_hybrid_2026_manifest.json").read_text(encoding="utf-8"))
    schema = json.loads((SCENARIOS / "scenario_schema.json").read_text(encoding="utf-8"))
    files = sorted(path for path in SCENARIOS.iterdir() if path.is_file() and path != OUTPUT)
    payload = {
        "manifest_version": "1.0",
        "hash_algorithm": "SHA-256",
        "app_version": app_version(),
        "model_version": model["version"],
        "data_snapshot": schema["data_snapshot"],
        "release_id": "bh26-2026.08-r1",
        "file_count": len(files),
        "files": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in files
        },
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(files)} hashes.")


if __name__ == "__main__":
    main()
