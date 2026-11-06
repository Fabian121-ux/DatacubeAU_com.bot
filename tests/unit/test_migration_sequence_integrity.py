from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "bot_core" / "migrations"
VALIDATOR_PATH = ROOT / "bot_core" / "scripts" / "validate_migration_sequence.py"
DEPLOY_SCRIPT = ROOT / "deploy" / "scripts" / "run-migrations.sh"

_spec = importlib.util.spec_from_file_location("zina_migration_sequence_validator", VALIDATOR_PATH)
assert _spec is not None and _spec.loader is not None
_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validator)
validate_migration_names = _validator.validate_migration_names
validate_migration_directory = _validator.validate_migration_directory


def test_sql_migration_numbers_are_unique_and_contiguous() -> None:
    """Validate the same chain that the deployment runner will apply."""
    validate_migration_directory(MIGRATIONS_DIR)


def test_migration_sequence_guard_accepts_a_contiguous_chain() -> None:
    validate_migration_names(["003_third.sql", "001_init.sql", "002_next.sql"])


@pytest.mark.parametrize(
    ("names", "message"),
    [
        (["001_init.sql", "003_gap.sql"], "contiguous"),
        (["001_init.sql", "001_duplicate.sql"], "unique"),
        (["001-init.sql"], "invalid SQL migration filenames"),
        ([], "no SQL migration files"),
    ],
)
def test_migration_sequence_guard_rejects_invalid_chains(
    names: list[str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_migration_names(names)


def test_migration_directory_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="directory does not exist"):
        validate_migration_directory(tmp_path / "missing")


def _run_deployment_with_invalid_bundle(
    tmp_path: Path,
    names: list[str] | None,
) -> subprocess.CompletedProcess[str]:
    migrations_dir = tmp_path / "migrations"
    if names is not None:
        migrations_dir.mkdir()
        for name in names:
            (migrations_dir / name).write_text("-- test fixture only\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    psql_marker = tmp_path / "psql-was-called"
    fake_psql = fake_bin / "psql"
    fake_psql.write_text(
        "#!/bin/sh\n"
        ': "${PSQL_MARKER:?}"\n'
        'printf "called\n" >> "$PSQL_MARKER"\n',
        encoding="utf-8",
    )
    fake_psql.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL_SYNC": "postgresql://unused.invalid/test",
            "APP_ROOT": str(ROOT),
            "MIGRATIONS_DIR": str(migrations_dir),
            "SEEDS_DIR": str(tmp_path / "seeds"),
            "PSQL_MARKER": str(psql_marker),
            "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
        }
    )
    return subprocess.run(
        ["sh", str(DEPLOY_SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


@pytest.mark.parametrize(
    ("names", "reason"),
    [
        (["001_init.sql", "003_gap.sql"], "gap"),
        (["001_init.sql", "001_duplicate.sql"], "duplicate"),
        (["001-init.sql"], "malformed filename"),
        ([], "empty migration directory"),
        (None, "missing migration directory"),
    ],
    ids=["gap", "duplicate", "malformed", "empty", "missing-directory"],
)
def test_deployment_preflight_rejects_invalid_bundle_before_any_psql_call(
    tmp_path: Path,
    names: list[str] | None,
    reason: str,
) -> None:
    result = _run_deployment_with_invalid_bundle(tmp_path, names)
    assert result.returncode != 0, f"expected {reason} to fail closed"
    assert not (tmp_path / "psql-was-called").exists(), (
        f"{reason} reached psql before migration preflight rejected it"
    )
    assert "migration" in (result.stdout + result.stderr).lower()
