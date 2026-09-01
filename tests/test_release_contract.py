from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


integrity = load_module("validate_integrity.py", "validate_integrity")


class ReleaseContractTests(unittest.TestCase):
    def test_full_integrity_contract(self) -> None:
        integrity.main()

    def test_candidate_identifiers_are_unique(self) -> None:
        manifest = json.loads(
            (ROOT / "data" / "scenarios" / "bau_hybrid_2026_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        identifiers = manifest["ensemble_candidate_ids"]
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_lookup_extrapolations_are_audited(self) -> None:
        manifest = json.loads(
            (ROOT / "data" / "scenarios" / "bau_hybrid_2026_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        integrity.validate_lookup_audit(manifest)
        generator = (
            ROOT / "science" / "scripts" / "build_joint_hybrid_2026.py"
        ).read_text(encoding="utf-8")
        self.assertIn("lookup_extrapolation_audit.csv", generator)
        for directory in (ROOT / "science" / "scripts", ROOT / "science" / "src"):
            for source in directory.rglob("*.py"):
                self.assertNotIn(
                    'filterwarnings("ignore")',
                    source.read_text(encoding="utf-8"),
                    source.relative_to(ROOT),
                )

    def test_ui_uses_named_columns(self) -> None:
        source = (ROOT / "src" / "ScenarioData.vala").read_text(encoding="utf-8")
        for column in (
            "year", "observed", "original_bau", "original_bau2",
            "hybrid_2026", "p10", "p90", "benchmark",
        ):
            self.assertIn(f'require_column (headers, "{column}"', source)
        self.assertNotIn("parse_value (fields[12])", source)
        window = (ROOT / "src" / "MainWindow.vala").read_text(encoding="utf-8")
        for column in (
            "test_start", "test_end", "origins", "historical_mape_pct",
            "historical_bias_pct", "bau2_level_anchored_mape_pct",
            "bau2_e2026_mape_pct",
        ):
            self.assertIn(f'require_column (headers, "{column}"', window)
        self.assertNotRegex(window, r"fields\[[0-9]+\]")


if __name__ == "__main__":
    unittest.main()
