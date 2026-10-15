"""Read-only preflight for unique SQL migration numbers and installed upgrade history.

Usage:
    python bot_core/scripts/check_migration_versions.py bot_core/migrations
    psql ... -Atc "SELECT version || E'\\t' || checksum FROM schema_migrations ORDER BY version" | \
      python bot_core/scripts/check_migration_versions.py bot_core/migrations --applied-manifest-stdin

Never connects to a database. The caller supplies installed migration filenames and SHA256 checksums via stdin.
It validates installed checksums before any database mutation; the runner still checks
individual checksums while applying SQL. It does not validate SQL semantics.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

MIGRATION_NAME = re.compile(r"(?P<version>[0-9]{3})_[A-Za-z0-9][A-Za-z0-9_.-]*\.sql\Z")


def validate_migrations(
    directory: Path,
    applied_versions: list[str] | None = None,
    applied_manifest: list[str] | None = None,
) -> list[str]:
    """Return deterministic fail-closed diagnostics; an empty list permits deployment."""
    if not directory.is_dir():
        return [f"migration directory missing: {directory}"]
    files = sorted(directory.glob("*.sql"), key=lambda path: path.name)
    if not files:
        return [f"no SQL migrations found in {directory}"]

    current_by_number: dict[str, str] = {}
    errors: list[str] = []
    for path in files:
        if not path.is_file() or path.is_symlink():
            errors.append(f"migration must be a regular file: {path.name}")
            continue
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            errors.append(f"malformed migration filename: {path.name}")
            continue
        number = match.group("version")
        prior = current_by_number.get(number)
        if prior is not None:
            errors.append(f"duplicate migration version {number}: {prior} and {path.name}")
        else:
            current_by_number[number] = path.name

    # A missing numeric slot changes the meaning of subsequent migrations. A PR
    # adding 035 on top of main 033 must not silently skip the conflicting 034.
    # Small isolated fixtures and partial migration bundles can start above 001;
    # only assert continuity when the checkout explicitly contains the first file.
    if "001" in current_by_number:
        numbers = sorted(int(number) for number in current_by_number)
        expected = set(range(1, numbers[-1] + 1))
        for missing in sorted(expected - set(numbers)):
            errors.append(f"missing migration version {missing:03d}: reconcile the ordered chain before deployment")

    # Validate every *installed* checksum before any new SQL executes. The deployment
    # runner checks checksums inside its migration loop, which is too late if an
    # earlier, newly introduced migration has already changed the database.
    if applied_manifest is not None and applied_versions is not None:
        errors.append("choose one installed migration input format, not both")
    installed_checksums: dict[str, str] = {}
    if applied_manifest is not None:
        applied_versions = []
        for raw in applied_manifest:
            if not raw.strip():
                continue
            fields = raw.split("\t")
            if len(fields) != 2 or not re.fullmatch(r"[a-fA-F0-9]{64}", fields[1]):
                errors.append(f"malformed installed migration manifest row: {raw!r}")
                continue
            installed, checksum = fields
            applied_versions.append(installed)
            if installed in installed_checksums:
                errors.append(f"duplicate installed migration manifest entry: {installed}")
            installed_checksums[installed] = checksum.lower()

    installed_by_number: dict[str, str] = {}
    for raw in applied_versions or []:
        installed = raw.strip()
        if not installed:
            continue
        match = MIGRATION_NAME.fullmatch(installed)
        if match is None:
            errors.append(f"malformed installed migration filename: {installed!r}")
            continue
        number = match.group("version")
        prior = installed_by_number.get(number)
        if prior is not None and prior != installed:
            errors.append(f"duplicate installed migration version {number}: {prior} and {installed}")
        installed_by_number[number] = installed
        current = current_by_number.get(number)
        if current is None:
            errors.append(
                f"installed migration missing from checkout: {installed}; "
                "manual upgrade reconciliation required"
            )
        elif current != installed:
            errors.append(
                f"installed migration version {number} changed filename: "
                f"database has {installed}, checkout has {current}; manual upgrade reconciliation required"
            )
        elif installed in installed_checksums:
            # The regex and symlink checks above already reject suspicious paths.
            path = directory / installed
            if not path.is_file() or path.is_symlink():
                errors.append(f"cannot checksum non-regular migration: {installed}")
                continue
            try:
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
            except OSError as exc:
                errors.append(f"cannot read installed migration for checksum: {installed}: {exc}")
                continue
            if digest != installed_checksums[installed]:
                errors.append(
                    f"installed migration checksum mismatch before deployment: {installed}; "
                    "manual upgrade reconciliation required"
                )
    # An installed history must be a contiguous *prefix* of the checked-out
    # migration chain. A gap in schema_migrations can mean that an earlier SQL
    # migration was never applied (or its evidence was lost). Applying it after a
    # later version is not a safe upgrade, even if filenames and checksums of
    # every *recorded* row still match. Partial test fixtures without 001 are
    # intentionally excluded; production checkouts include migration 001.
    if "001" in current_by_number and installed_by_number:
        installed_numbers = {int(number) for number in installed_by_number}
        last_installed = max(installed_numbers)
        for missing in sorted(set(range(1, last_installed + 1)) - installed_numbers):
            errors.append(
                f"installed migration history is not a contiguous prefix: "
                f"missing version {missing:03d} before installed version "
                f"{last_installed:03d}; manual upgrade reconciliation required"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--applied-versions-stdin", action="store_true",
                        help="read schema_migrations.version names from stdin (one per line)")
    parser.add_argument("--applied-manifest-stdin", action="store_true",
                        help="read installed filename and SHA256 as TAB-separated rows from stdin")
    args = parser.parse_args(argv)
    if args.applied_versions_stdin and args.applied_manifest_stdin:
        parser.error("choose one installed migration input format")
    rows = sys.stdin.read().splitlines() if (args.applied_versions_stdin or args.applied_manifest_stdin) else None
    errors = validate_migrations(
        args.directory,
        applied_versions=rows if args.applied_versions_stdin else None,
        applied_manifest=rows if args.applied_manifest_stdin else None,
    )
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"Migration version preflight passed: {args.directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
