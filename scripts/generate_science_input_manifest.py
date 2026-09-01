#!/usr/bin/env python3
"""Generate deterministic hashes for the frozen scientific input snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT / "science"
OUTPUT = SCIENCE / "data" / "input_manifest.json"
REMOTE = SCIENCE / "data" / "remote_inputs.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    remote_manifest = json.loads(REMOTE.read_text(encoding="utf-8"))
    remote_files = remote_manifest["files"]
    remote_paths = {ROOT / relative for relative in remote_files}
    candidates = [
        path
        for directory in (SCIENCE / "data" / "raw", SCIENCE / "data" / "processed")
        for path in directory.rglob("*")
        if path.is_file() and path not in remote_paths
    ]
    candidates.extend(
        [
            SCIENCE / "data" / "registry.csv",
            REMOTE,
            SCIENCE / "vendor" / "world3_03" / "World3_03_Scenarios.mdl",
        ]
    )
    files = sorted(set(candidates))
    payload = {
        "manifest_version": "1.1",
        "hash_algorithm": "SHA-256",
        "snapshot_date": "2026-08-30",
        "file_count": len(files) + len(remote_files),
        "files": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in files
        },
        "remote_files": remote_files,
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)} with {len(files)} local and "
        f"{len(remote_files)} remote input hashes."
    )


if __name__ == "__main__":
    main()
