#!/usr/bin/env python3
"""Report model evidence without turning an unfavorable result into a build failure."""

from __future__ import annotations

import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "data" / "scenarios"
KEYS = [
    "population",
    "industry_per_capita",
    "food_per_capita",
    "pollution_pressure",
    "human_welfare",
]


def rows(filename: str) -> list[dict[str, str]]:
    with (SCENARIOS / filename).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ordered(items: list[dict[str, str]], filename: str) -> dict[str, dict[str, str]]:
    if [item["key"] for item in items] != KEYS:
        raise AssertionError(f"{filename} does not follow the declared indicator order")
    return {item["key"]: item for item in items}


def main() -> None:
    fit = ordered(rows("fit_diagnostics.csv"), "fit_diagnostics.csv")
    recent = ordered(rows("backtest_2019_latest.csv"), "backtest_2019_latest.csv")
    multi = ordered(rows("backtest_multi_origin.csv"), "backtest_multi_origin.csv")

    print("Raport științific (performanța este raportată, nu impusă de build):")
    print("indicator | MAPE istoric | holdout hibrid/BAU2 | multi-origin hibrid/BAU2 | verdict")
    recent_wins = 0
    multi_wins = 0
    for key in KEYS:
        historical = float(fit[key]["historical_mape_pct"])
        recent_hybrid = float(recent[key]["bau2_e2026_mape_pct"])
        recent_bau2 = float(recent[key]["bau2_level_anchored_mape_pct"])
        multi_hybrid = float(multi[key]["bau2_e2026_mape_pct"])
        multi_bau2 = float(multi[key]["bau2_level_anchored_mape_pct"])
        recent_better = recent_hybrid <= recent_bau2
        multi_better = multi_hybrid <= multi_bau2
        recent_wins += int(recent_better)
        multi_wins += int(multi_better)
        verdict = "ambele mai bune" if recent_better and multi_better else (
            "mixt" if recent_better or multi_better else "ambele mai slabe"
        )
        print(
            f"{key} | {historical:.2f}% | {recent_hybrid:.2f}/{recent_bau2:.2f}% | "
            f"{multi_hybrid:.2f}/{multi_bau2:.2f}% | {verdict}"
        )

    if recent_wins < len(KEYS):
        print(f"AVERTISMENT: hibridul câștigă numai {recent_wins}/{len(KEYS)} holdouturi recente.")
    if multi_wins < len(KEYS):
        print(f"AVERTISMENT: hibridul câștigă numai {multi_wins}/{len(KEYS)} validări multi-origin.")
    print("Raport științific generat cu succes; verdictul de promovare este separat.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, ValueError) as error:
        print(f"Eroare în raportul științific: {error}", file=sys.stderr)
        raise SystemExit(1)
