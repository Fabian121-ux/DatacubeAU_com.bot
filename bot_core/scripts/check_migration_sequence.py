#!/usr/bin/env python3
"""Fail-closed, read-only migration filename preflight shared by deploy and CI.

This checks *number allocation*, not installed database state or migration SQL.
It deliberately does not connect to PostgreSQL or rewrite any migration file.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

MIGRATION_NAME = re.compile(r"(?P<sequence>[0-9]{3})_[A-Za-z0-9][A-Za-z0-9_-]*\.sql\Z")


def validate(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise ValueError(f"Migration directory missing: {directory}")
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise ValueError(f"No SQL migrations found in {directory}")
    by_sequence: dict[str, Path] = {}
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Migration must be a regular, non-symlink file: {path}")
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"Invalid migration filename (expected NNN_name.sql): {path.name}")
        sequence = match.group("sequence")
        previous = by_sequence.get(sequence)
        if previous is not None:
            raise ValueError(
                f"Migration sequence {sequence} collision: {previous.name} and {path.name}. "
                "Renumber and reconcile the installed schema_migrations ledger before merging."
            )
        by_sequence[sequence] = path
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("migration_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        files = validate(args.migration_directory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Migration sequence preflight OK: {len(files)} unique SQL files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
