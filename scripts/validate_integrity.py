#!/usr/bin/env python3
"""Fail only on broken release contracts, provenance, metadata, or data integrity."""

from __future__ import annotations

import configparser
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


APP_ID = "io.github.laurentiustaicu.World3Empirical"
ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "data" / "scenarios"


def fail(message: str) -> None:
    raise AssertionError(message)


def app_version() -> str:
    text = (ROOT / "meson.build").read_text(encoding="utf-8")
    match = re.search(r"version:\s*'([^']+)'", text)
    if not match:
        fail("meson.build does not expose a project version")
    return match.group(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    if not headers or not rows:
        fail(f"{path.relative_to(ROOT)} is empty")
    if len(headers) != len(set(headers)):
        fail(f"{path.relative_to(ROOT)} contains duplicate column names")
    if any(None in row for row in rows):
        fail(f"{path.relative_to(ROOT)} has more row fields than header fields")
    return headers, rows


def number(value: str, path: Path, field: str, *, optional: bool = False) -> float:
    if value == "" and optional:
        return math.nan
    try:
        parsed = float(value)
    except ValueError:
        fail(f"{path.relative_to(ROOT)} contains a non-numeric {field}: {value!r}")
    if not math.isfinite(parsed):
        fail(f"{path.relative_to(ROOT)} contains a non-finite {field}")
    return parsed


def validate_metadata(version: str) -> None:
    ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml")
    ET.parse(ROOT / "data" / "icons" / f"{APP_ID}.svg")
    appstream = ET.parse(ROOT / "data" / f"{APP_ID}.metainfo.xml").getroot()
    releases = appstream.find("releases")
    if releases is None or len(releases) == 0 or releases[0].get("version") != version:
        fail("The newest AppStream release must match the Meson project version")

    desktop = configparser.ConfigParser(interpolation=None)
    desktop.read(ROOT / "data" / f"{APP_ID}.desktop", encoding="utf-8")
    entry = desktop["Desktop Entry"]
    if entry.get("Exec") != APP_ID or entry.get("Icon") != APP_ID:
        fail("Desktop Exec/Icon must match the application id")

    flatpak = (ROOT / f"{APP_ID}.yml").read_text(encoding="utf-8")
    for required in (
        f"app-id: {APP_ID}",
        "runtime: io.elementary.Platform",
        "runtime-version: '8'",
        "sdk: io.elementary.Sdk",
        "--socket=fallback-x11",
        "--socket=wayland",
    ):
        if required not in flatpak:
            fail(f"Missing Flatpak manifest setting: {required}")

    meson = (ROOT / "meson.build").read_text(encoding="utf-8")
    if "find_library('m', required: true)" not in meson or "BuildConfig.vala.in" not in meson:
        fail("Meson must link libm and generate BuildConfig from project_version")
    main_window = (ROOT / "src" / "MainWindow.vala").read_text(encoding="utf-8")
    if "dialog.version = BuildConfig.VERSION;" not in main_window:
        fail("The About dialog must use the generated project version")


def validate_indicator(path: Path, status: str, required: set[str]) -> None:
    headers, rows = read_csv(path)
    missing = required.difference(headers)
    if missing:
        fail(f"{path.name} is missing columns: {sorted(missing)}")

    years = [int(number(row["year"], path, "year")) for row in rows]
    if years != list(range(1950, 2101)):
        fail(f"{path.name} must contain one ordered row for every year 1950–2100")

    observed_rows: list[dict[str, str]] = []
    forecast_rows = 0
    for row in rows:
        for field in ("original_bau", "original_bau2", "hybrid_2026"):
            number(row[field], path, field)
        if row["observed"]:
            number(row["observed"], path, "observed")
            observed_rows.append(row)
        if row["forecast_median"]:
            number(row["forecast_median"], path, "forecast_median")
            forecast_rows += 1
        p10 = number(row["p10"], path, "p10", optional=True)
        p90 = number(row["p90"], path, "p90", optional=True)
        if math.isnan(p10) != math.isnan(p90):
            fail(f"{path.name} has an incomplete P10–P90 pair in {row['year']}")
        if not math.isnan(p10) and p10 > p90:
            fail(f"{path.name} has reversed P10–P90 values in {row['year']}")
        if row["benchmark"]:
            number(row["benchmark"], path, "benchmark")

    if forecast_rows == 0:
        fail(f"{path.name} contains no forecast segment")
    if status == "latent" and observed_rows:
        fail(f"{path.name} is latent but contains observations")
    if status != "latent" and not observed_rows:
        fail(f"{path.name} must contain observations")
    if observed_rows:
        latest = observed_rows[-1]
        if not math.isclose(
            number(latest["observed"], path, "observed"),
            number(latest["hybrid_2026"], path, "hybrid_2026"),
            rel_tol=0,
            abs_tol=1e-6,
        ):
            fail(f"{path.name} is not anchored to its latest observation")


def validate_model_contract(model: dict[str, object]) -> None:
    if model.get("model") != "BAU Hybrid 2026 Joint":
        fail("Scientific manifest model identifier changed unexpectedly")
    if model.get("structural_model") != "official World3-03 scenario 2 (BAU2)":
        fail("BAU Hybrid must remain structurally based on World3-03 BAU2")
    if len(model.get("central_parameters", {})) != 7:
        fail("Scientific manifest must expose the common seven-parameter vector")
    ensemble = model.get("ensemble_candidate_ids", [])
    if len(ensemble) != len(set(ensemble)):
        fail("Scientific ensemble contains duplicate candidate identifiers")
    if model.get("central_candidate_id") not in ensemble:
        fail("Central candidate must be an actual ensemble member")
    if model.get("validation_candidate_id") == model.get("production_candidate_id"):
        fail("Validation and production candidates must remain separate")
    if model.get("central_plausibility_violation_count") != 0:
        fail("Central candidate violates a declared guardrail")


def validate_lookup_audit(model: dict[str, object]) -> None:
    path = SCENARIOS / "lookup_extrapolation_audit.csv"
    headers, rows = read_csv(path)
    required = {"candidate_id", "total", "above", "below", "unique"}
    if not required.issubset(headers):
        fail(f"{path.name} is missing columns: {sorted(required.difference(headers))}")
    expected_count = int(model.get("candidate_count", 0))
    identifiers = [int(number(row["candidate_id"], path, "candidate_id")) for row in rows]
    if identifiers != list(range(expected_count)):
        fail(f"{path.name} must contain every candidate exactly once in order")
    for row in rows:
        total = int(number(row["total"], path, "total"))
        above = int(number(row["above"], path, "above"))
        below = int(number(row["below"], path, "below"))
        unique = int(number(row["unique"], path, "unique"))
        if total != above + below or unique < 0 or unique > total:
            fail(f"{path.name} contains inconsistent warning counts")


def validate_hashes(version: str, model_version: str) -> None:
    path = SCENARIOS / "release_integrity.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("app_version") != version:
        fail("Integrity manifest app version differs from Meson")
    if manifest.get("model_version") != model_version:
        fail("Integrity manifest model version differs from scientific manifest")
    expected_paths = {
        str(item.relative_to(ROOT))
        for item in SCENARIOS.iterdir()
        if item.is_file() and item != path
    }
    declared = manifest.get("files", {})
    if set(declared) != expected_paths:
        fail("Integrity manifest file set differs from packaged scenario files")
    for relative, expected in declared.items():
        if sha256(ROOT / relative) != expected:
            fail(f"SHA-256 mismatch for {relative}; regenerate the integrity manifest")


def validate_scientific_inputs(snapshot: str) -> None:
    path = ROOT / "science" / "data" / "input_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("snapshot_date") != snapshot:
        fail("Scientific input snapshot date differs from the scenario schema")
    declared = manifest.get("files", {})
    remote = manifest.get("remote_files", {})
    if manifest.get("file_count") != len(declared) + len(remote) or not declared:
        fail("Scientific input manifest has an invalid file count")
    for relative, expected in declared.items():
        candidate = ROOT / relative
        if not candidate.is_file() or sha256(candidate) != expected:
            fail(f"Scientific input SHA-256 mismatch: {relative}")

    remote_path = ROOT / "science" / "data" / "remote_inputs.json"
    remote_manifest = json.loads(remote_path.read_text(encoding="utf-8"))
    if remote_manifest.get("files") != remote or not remote:
        fail("Scientific remote-input declaration differs from the frozen manifest")
    for relative, metadata in remote.items():
        expected = metadata.get("sha256", "")
        url = metadata.get("url", "")
        size = metadata.get("size_bytes", 0)
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            fail(f"Invalid remote-input SHA-256: {relative}")
        if not str(url).startswith("https://") or not isinstance(size, int) or size <= 0:
            fail(f"Invalid remote-input provenance: {relative}")
        candidate = ROOT / relative
        if candidate.exists() and (
            not candidate.is_file()
            or candidate.stat().st_size != size
            or sha256(candidate) != expected
        ):
            fail(f"Downloaded scientific input differs from its frozen hash: {relative}")


def main() -> None:
    version = app_version()
    validate_metadata(version)
    schema = json.loads((SCENARIOS / "scenario_schema.json").read_text(encoding="utf-8"))
    model = json.loads((SCENARIOS / "bau_hybrid_2026_manifest.json").read_text(encoding="utf-8"))
    if schema.get("app_release") != version:
        fail("Scenario schema app release differs from Meson")
    if schema.get("model_version") != model.get("version"):
        fail("Scenario schema model version differs from the scientific manifest")

    required = set(schema["indicator_required_columns"])
    for filename, status in schema["indicator_files"].items():
        validate_indicator(SCENARIOS / filename, status, required)
    for filename in schema["diagnostic_files"]:
        read_csv(SCENARIOS / filename)

    validate_model_contract(model)
    validate_lookup_audit(model)
    validate_hashes(version, str(model["version"]))
    validate_scientific_inputs(str(schema["data_snapshot"]))
    print(
        f"Validare de integritate reușită: aplicație {version}, model {model['version']}, "
        f"schemă {schema['schema_version']} și hash-uri SHA-256 verificate."
    )


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ET.ParseError, json.JSONDecodeError) as error:
        print(f"Eroare de integritate: {error}", file=sys.stderr)
        raise SystemExit(1)
