from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


integrity = load_module("validate_integrity.py", "validate_integrity")
reproduction = load_module(
    "reproduce_scientific_results.py", "reproduce_scientific_results"
)


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

    def test_csv_reproduction_accepts_machine_precision_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / "generated.csv"
            packaged = root / "packaged.csv"
            generated.write_text("name,value\ncentral,0.009371596496610582\n", encoding="utf-8")
            packaged.write_text("name,value\ncentral,0.009371596496610493\n", encoding="utf-8")
            difference = reproduction.compare_csv(generated, packaged)
            self.assertGreater(difference, 0)

    def test_csv_reproduction_rejects_material_numeric_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / "generated.csv"
            packaged = root / "packaged.csv"
            generated.write_text("name,value\ncentral,1.000001\n", encoding="utf-8")
            packaged.write_text("name,value\ncentral,1.0\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "absolute difference"):
                reproduction.compare_csv(generated, packaged)

    def test_csv_reproduction_rejects_text_or_schema_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / "generated.csv"
            packaged = root / "packaged.csv"
            generated.write_text("name,value\nchanged,1\n", encoding="utf-8")
            packaged.write_text("name,value\ncentral,1\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "changed"):
                reproduction.compare_csv(generated, packaged)

    def test_json_reproduction_is_tolerant_only_for_floats(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / "generated.json"
            packaged = root / "packaged.json"
            generated.write_text(
                '{"candidate": "c001", "score": 0.009371596496610582}\n',
                encoding="utf-8",
            )
            packaged.write_text(
                '{"candidate": "c001", "score": 0.009371596496610493}\n',
                encoding="utf-8",
            )
            self.assertGreater(reproduction.compare_json(generated, packaged), 0)
            generated.write_text(
                '{"candidate": "c002", "score": 0.009371596496610582}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "c002"):
                reproduction.compare_json(generated, packaged)


if __name__ == "__main__":
    unittest.main()
