from __future__ import annotations

import re
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "bot_core" / "migrations"
MIGRATION_NAME = re.compile(r"(?P<number>\d{3})_[a-z0-9_]+\.sql\Z")


def test_sql_migration_numbers_are_unique_and_contiguous() -> None:
    """Reject PRs whose migrations skip an unmerged predecessor.

    The Tests workflow applies every SQL migration found in the checkout. Without
    this assertion, a feature branch can pass by applying (for example) 038 directly
    after 033, even though its migration depends on schema changes in 034-037.
    GitHub's pull_request merge ref includes the current base branch, so migrations
    can be merged in order and each dependent PR becomes green once its predecessors
    are integrated.
    """
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    assert files, f"no SQL migrations found in {MIGRATIONS_DIR}"

    parsed: list[tuple[int, str]] = []
    invalid_names: list[str] = []
    for path in files:
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            invalid_names.append(path.name)
            continue
        parsed.append((int(match.group("number")), path.name))

    assert not invalid_names, (
        "Every SQL migration must use the NNN_description.sql naming convention; "
        f"invalid filenames: {invalid_names}"
    )

    numbers = [number for number, _ in parsed]
    assert len(numbers) == len(set(numbers)), (
        "SQL migration numbers must be unique; duplicates: "
        f"{[number for number in numbers if numbers.count(number) > 1]}"
    )

    expected = list(range(1, len(numbers) + 1))
    assert numbers == expected, (
        "SQL migration chain must be contiguous from 001. "
        f"Expected {expected[0]:03d}..{expected[-1]:03d}, "
        f"found {[f'{number:03d}' for number in numbers]}. "
        "Merge prerequisite migration PRs in sequence before dependent PRs."
    )
