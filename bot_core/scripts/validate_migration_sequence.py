from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


MIGRATION_NAME = re.compile(r"(?P<number>\d{3})_[a-z0-9_]+\.sql\Z")


def validate_migration_names(names: Iterable[str]) -> list[tuple[int, str]]:
    """Reject malformed, duplicate, or non-contiguous SQL migration filenames."""
    sorted_names = sorted(names)
    if not sorted_names:
        raise ValueError("no SQL migration files found")

    parsed: list[tuple[int, str]] = []
    invalid_names: list[str] = []
    for name in sorted_names:
        match = MIGRATION_NAME.fullmatch(name)
        if match is None:
            invalid_names.append(name)
            continue
        parsed.append((int(match.group("number")), name))

    if invalid_names:
        raise ValueError(
            "invalid SQL migration filenames (expected NNN_description.sql): "
            + ", ".join(invalid_names)
        )

    numbers = [number for number, _ in parsed]
    counts = Counter(numbers)
    duplicates = sorted(number for number, count in counts.items() if count > 1)
    if duplicates:
        raise ValueError(
            "SQL migration numbers must be unique; duplicates: "
            + ", ".join(f"{number:03d}" for number in duplicates)
        )

    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        found = ", ".join(f"{number:03d}" for number in numbers)
        raise ValueError(
            "SQL migration chain must be contiguous from 001; "
            f"expected 001..{len(numbers):03d}, found [{found}]"
        )

    return parsed


def validate_migration_directory(directory: str | Path) -> list[tuple[int, str]]:
    """Validate every .sql migration file that the shell runner would apply."""
    path = Path(directory)
    if not path.is_dir():
        raise ValueError(f"migration directory does not exist: {path}")
    return validate_migration_names(file.name for file in path.glob("*.sql"))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: validate_migration_sequence.py MIGRATIONS_DIR", file=sys.stderr)
        return 2
    try:
        migrations = validate_migration_directory(args[0])
    except ValueError as exc:
        print(f"Migration preflight failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Validated contiguous SQL migration chain: "
        f"001..{migrations[-1][0]:03d} ({len(migrations)} files)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
