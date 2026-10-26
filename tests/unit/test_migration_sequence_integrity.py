from __future__ import annotations

import re
from pathlib import Path

import pytest


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "bot_core" / "migrations"
MIGRATION_NAME = re.compile(r"(?P<number>\d{3})_[a-z0-9_]+\.sql\Z")


def _validate_migration_names(names: list[str]) -> None:
    """Fail closed on malformed, duplicate, or non-contiguous migration names."""
    parsed: list[tuple[int, str]] = []
    invalid_names: list[str] = []
    for name in sorted(names):
        match = MIGRATION_NAME.fullmatch(name)
        if match is None:
            invalid_names.append(name)
            continue
        parsed.append((int(match.group("number")), name))

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
    _validate_migration_names([path.name for path in files])


def test_migration_sequence_guard_accepts_a_contiguous_chain() -> None:
    _validate_migration_names(["003_third.sql", "001_init.sql", "002_next.sql"])


@pytest.mark.parametrize(
    ("names", "message"),
    [
        (["001_init.sql", "003_gap.sql"], "contiguous"),
        (["001_init.sql", "001_duplicate.sql"], "unique"),
        (["001-init.sql"], "invalid filenames"),
    ],
)
def test_migration_sequence_guard_rejects_invalid_chains(
    names: list[str],
    message: str,
) -> None:
    with pytest.raises(AssertionError, match=message):
        _validate_migration_names(names)
