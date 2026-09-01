#!/usr/bin/env python3
"""Fetch large frozen scientific inputs and verify them before use."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
REMOTE_MANIFEST = ROOT / "science" / "data" / "remote_inputs.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid(path: Path, metadata: dict[str, object]) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == int(metadata["size_bytes"])
        and sha256(path) == metadata["sha256"]
    )


def fetch(relative: str, metadata: dict[str, object], *, check_only: bool) -> None:
    destination = ROOT / relative
    if valid(destination, metadata):
        print(f"Intrare științifică verificată: {relative}")
        return
    if check_only:
        raise RuntimeError(f"Intrare științifică absentă sau coruptă: {relative}")

    url = str(metadata["url"])
    if not url.startswith("https://"):
        raise RuntimeError(f"Sursa externă nu folosește HTTPS: {relative}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "World3-Empirical-reproducibility/0.10.1"},
        )
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        if not valid(temporary, metadata):
            raise RuntimeError(
                f"Fișierul descărcat nu corespunde snapshotului înghețat: {relative}"
            )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Intrare științifică descărcată și verificată: {relative}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verifică fișierele existente fără acces la rețea.",
    )
    arguments = parser.parse_args()
    manifest = json.loads(REMOTE_MANIFEST.read_text(encoding="utf-8"))
    for relative, metadata in manifest["files"].items():
        fetch(relative, metadata, check_only=arguments.check_only)


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Eroare la intrările științifice: {error}", file=sys.stderr)
        raise SystemExit(1)
