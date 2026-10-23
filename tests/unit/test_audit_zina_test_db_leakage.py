from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_zina_test_db_leakage.py"


@pytest.mark.parametrize(
    ("database_url", "expected_message"),
    [
        (
            "postgresql+asyncpg://postgres:postgres@db.example.com:5432/datacube_bot_test",
            "isolated local datacube_bot_test database",
        ),
        (
            "postgresql+asyncpg://postgres:postgres@localhost:5432/another_database",
            "isolated local datacube_bot_test database",
        ),
        (
            "postgresql://postgres:postgres@localhost:5432/datacube_bot_test",
            "PostgreSQL async URL",
        ),
        (
            "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test?host=remote.example.com",
            "query parameters are not allowed",
        ),
        (
            "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test?database=production_db",
            "query parameters are not allowed",
        ),
        (
            "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test?port=5433",
            "query parameters are not allowed",
        ),
        (
            "postgresql+asyncpg://postgres:postgres@localhost:5433/datacube_bot_test",
            "disposable PostgreSQL port 5432",
        ),
        (
            "postgresql+asyncpg://postgres:postgres@localhost:not-a-port/datacube_bot_test",
            "valid PostgreSQL port",
        ),
        ("", "isolated local datacube_bot_test database"),
    ],
)
def test_leakage_audit_refuses_unsafe_database_urls(
    database_url: str, expected_message: str
) -> None:
    # Exercise the real CLI entry point, but give it an invalid URL so it must exit
    # before creating an engine or opening any database connection.
    env = os.environ.copy()
    # Local test runs do not necessarily inherit GitHub Actions' runner marker.
    # Set it explicitly so these cases exercise URL validation, not the CI-only gate.
    env["GITHUB_ACTIONS"] = "true"
    env["DATABASE_URL"] = database_url
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode != 0
    assert expected_message in (completed.stdout + completed.stderr)

def test_leakage_audit_refuses_to_run_outside_github_actions() -> None:
    env = os.environ.copy()
    env.pop("GITHUB_ACTIONS", None)
    env["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test"
    )
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode != 0
    assert "only run inside GitHub Actions" in (completed.stdout + completed.stderr)

