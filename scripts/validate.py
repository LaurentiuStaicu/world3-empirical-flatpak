#!/usr/bin/env python3
"""Run release-integrity checks and report scientific performance separately."""

from validate_integrity import main as validate_integrity
from validate_science import main as validate_science


def main() -> None:
    validate_integrity()
    validate_science()


if __name__ == "__main__":
    main()
