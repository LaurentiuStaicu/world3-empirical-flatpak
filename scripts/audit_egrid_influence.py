"""Reproduce error attribution from retained public eGRID cohorts."""
import json

from audit_egrid_temporal import ROOT, read_cohort
from world3_empirical.egrid_influence import error_influence


def main():
    result = {
        "interpretation": "Post-hoc error attribution using known target outcomes; no model promotion or exclusions.",
        "transitions": [error_influence(read_cohort(y), read_cohort(y+1), y, y+1) for y in (2021, 2022)],
    }
    destination = ROOT / "science/data/energy_audit/egrid-influence.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    temporary.replace(destination)
    for transition in result["transitions"]:
        print(transition["training_year"], {
            name: signal["top_error_shares_pct"] for name, signal in transition["signals"].items()
        })


if __name__ == "__main__":
    main()
