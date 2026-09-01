"""Command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from .model import run_scenario
from .scenarios import load_scenarios


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="world3-empirical")
    subparsers = parser.add_subparsers(dest="command", required=True)
    simulate = subparsers.add_parser("simulate", help="Run a declared scenario")
    simulate.add_argument("--scenario", choices=sorted(load_scenarios()), default="world3_standard")
    simulate.add_argument("--year-min", type=int, default=1900)
    simulate.add_argument("--year-max", type=int, default=2100)
    simulate.add_argument("--dt", type=float, default=0.5)
    simulate.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "simulate":
        result = run_scenario(args.scenario, year_min=args.year_min, year_max=args.year_max, dt=args.dt)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.frame.to_csv(args.output, index=False)
        print(f"Saved {len(result.frame)} rows to {args.output}")
        print(f"Scenario status: {result.scenario.evidence_status}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

