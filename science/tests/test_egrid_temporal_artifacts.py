import gzip
import json
import math
from pathlib import Path
import unittest

from world3_empirical.egrid_audit import audit
from world3_empirical.egrid_temporal import temporal_stability_audit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "science/data/energy_audit"


def cohort(year):
    name = "egrid-cohort.json.gz" if year == 2023 else f"egrid{year}-cohort.json.gz"
    with gzip.open(DATA / name, "rt") as source:
        return json.load(source)


class EgridTemporalArtifactTests(unittest.TestCase):
    def test_published_annual_cohorts_reproduce_audits(self):
        for year in (2021, 2022):
            rows = cohort(year)
            actual, selected = audit(rows, year)
            published = json.loads((DATA / f"egrid{year}-audit.json").read_text())
            self.assertEqual(selected, rows)
            self.assertEqual(actual["input_plants"], published["eligible_plants"])
            self.assertEqual(actual["eligible_plants"], published["eligible_plants"])
            actual_groups = actual["groups_by_co2_and_heat_source"]
            published_groups = published["groups_by_co2_and_heat_source"]
            self.assertEqual(actual_groups.keys(), published_groups.keys())
            for source, actual_group in actual_groups.items():
                for metric, value in actual_group.items():
                    expected = published_groups[source][metric]
                    if isinstance(value, float):
                        self.assertTrue(math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-8))
                    else:
                        self.assertEqual(value, expected)

    def test_published_temporal_results_reproduce_exactly(self):
        published = json.loads((DATA / "egrid-temporal-audit.json").read_text())
        expected = [
            temporal_stability_audit(cohort(2021), cohort(2022), 2021, 2022),
            temporal_stability_audit(cohort(2022), cohort(2023), 2022, 2023),
        ]
        self.assertEqual(published["transitions"], expected)

    def test_plant_persistence_is_not_promoted(self):
        published = json.loads((DATA / "egrid-temporal-audit.json").read_text())
        for transition in published["transitions"]:
            self.assertGreater(transition["matched_share_of_target_generation_pct"], 90)
            for signal in transition["signals"].values():
                plant = signal["plant_specific_persistence"]
                mean = signal["training_cohort_mean_persistence"]
                self.assertTrue(plant["wmape_change_defined"])
                self.assertGreater(
                    plant["quantity_weighted_absolute_percentage_error_pct"],
                    mean["quantity_weighted_absolute_percentage_error_pct"],
                )

    def test_source_metadata_is_explicit_and_raw_workbooks_are_external(self):
        expected = {
            2021: ("2023-01-30", "0bab3376509c79168ba19dff111e8a5ca7724043229af47af5cb5b6f71465644"),
            2022: ("2024-01-30", "c73fdc561aa402d0f6ed3cc35e5d961bee6af6e003c9c035b40f757f8480b76b"),
        }
        for year, (release_date, sha256) in expected.items():
            metadata = json.loads((DATA / f"egrid{year}-source.json").read_text())
            self.assertEqual(metadata["data_year"], year)
            self.assertEqual(metadata["release_date"], release_date)
            self.assertEqual(metadata["sha256"], sha256)
            self.assertFalse(metadata["raw_file_in_repository"])


if __name__ == "__main__":
    unittest.main()
