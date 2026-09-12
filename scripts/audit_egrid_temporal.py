"""Generate release-lagged year-to-year eGRID stability diagnostics."""
from pathlib import Path
import gzip
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "science/src"), str(ROOT / "science/vendor")]
from world3_empirical.egrid_temporal import temporal_stability_audit


def read_cohort(year):
    name = "egrid-cohort.json.gz" if year == 2023 else f"egrid{year}-cohort.json.gz"
    with gzip.open(ROOT / "science/data/energy_audit" / name, "rt") as source:
        return json.load(source)


def main():
    output = ROOT / "science/data/energy_audit/egrid-temporal-audit.json"
    result = {
        "audit_type": "release_lagged_temporal_stability_hindcast",
        "transitions": [
            temporal_stability_audit(read_cohort(2021), read_cohort(2022), 2021, 2022),
            temporal_stability_audit(read_cohort(2022), read_cohort(2023), 2022, 2023),
        ],
    }
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    temporary.replace(output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
