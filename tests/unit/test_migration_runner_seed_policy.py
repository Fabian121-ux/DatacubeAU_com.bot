from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "deploy" / "scripts" / "run-migrations.sh"
VALIDATION_SCRIPT = ROOT / "scripts" / "validate_zina_seed_policy.sh"


def test_invalid_local_seed_flag_fails_before_database_access() -> None:
    env = os.environ.copy()
    env["DATABASE_URL_SYNC"] = "postgresql://postgres:postgres@localhost:5432/datacube_bot_test"
    env["RUN_LOCAL_SEEDS"] = "yes"

    result = subprocess.run(
        ["sh", str(RUNNER)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode != 0
    assert "RUN_LOCAL_SEEDS must be exactly 'true' or 'false'" in (result.stdout + result.stderr)


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") != "true",
    reason="requires the disposable PostgreSQL service provided by GitHub Actions",
)
def test_deployment_runner_local_seed_policy_on_isolated_postgres() -> None:
    result = subprocess.run(
        ["bash", str(VALIDATION_SCRIPT)],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert (
        "local fixture seeds are opt-in, default redeploy preserves edits, "
        "and explicit opt-in remains functional"
    ) in output


@pytest.mark.parametrize("deployment_env", ["production", "staging", ""])
def test_local_seed_opt_in_requires_explicit_nonproduction_environment(deployment_env: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL_SYNC"] = "postgresql://postgres:postgres@localhost:5432/datacube_bot_test"
    env["RUN_LOCAL_SEEDS"] = "true"
    if deployment_env:
        env["ZINA_DEPLOYMENT_ENV"] = deployment_env
    else:
        env.pop("ZINA_DEPLOYMENT_ENV", None)

    result = subprocess.run(
        ["sh", str(RUNNER)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode != 0
    assert "RUN_LOCAL_SEEDS=true requires ZINA_DEPLOYMENT_ENV=development or test" in (
        result.stdout + result.stderr
    )

@pytest.mark.parametrize(
    ("database_url", "expected_message"),
    [
        (
            "postgresql://postgres:postgres@postgres:5432/datacube_bot",
            "target host must be local or host.docker.internal",
        ),
        (
            "postgresql://zina:secret@db.production.example:5432/zina_disposable",
            "target host must be local or host.docker.internal",
        ),
        (
            "postgresql://postgres:postgres@localhost:5432/datacube_bot",
            "database name must identify a disposable",
        ),
        (
            "postgresql://postgres:postgres@localhost:5432/test_real_database",
            "database name must identify a disposable",
        ),
        (
            "postgresql://postgres:postgres@localhost:5432/dev_production_backup",
            "database name must identify a disposable",
        ),
        (
            "postgresql://postgres:postgres@localhost:5432/zina_seed_policy_production",
            "database name must identify a disposable",
        ),
        (
            "postgresql://postgres:postgres@localhost:5432/zina_disposable?host=prod.example",
            "query parameters/fragments are forbidden",
        ),
        (
            "postgresql://postgres:postgres@localhost:not-a-port/zina_disposable",
            "invalid host or port",
        ),
    ],
)
def test_local_seed_opt_in_rejects_non_disposable_database_targets(
    database_url: str, expected_message: str
) -> None:
    # Even an explicitly overridden development marker must not permit local fixture
    # upserts against the production Compose service/database or an arbitrary remote DB.
    env = os.environ.copy()
    env["DATABASE_URL_SYNC"] = database_url
    env["RUN_LOCAL_SEEDS"] = "true"
    env["ZINA_DEPLOYMENT_ENV"] = "development"

    result = subprocess.run(
        ["sh", str(RUNNER)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode != 0
    assert expected_message in (result.stdout + result.stderr)


def test_ci_seed_namespace_is_refused_outside_github_actions() -> None:
    env = os.environ.copy()
    env.pop("GITHUB_ACTIONS", None)
    env["GITHUB_RUN_ID"] = "123"
    env["GITHUB_RUN_ATTEMPT"] = "1"
    env["DATABASE_URL_SYNC"] = "postgresql://postgres:postgres@localhost:5432/zina_seed_policy_123_1"
    env["RUN_LOCAL_SEEDS"] = "true"
    env["ZINA_DEPLOYMENT_ENV"] = "development"

    result = subprocess.run(
        ["sh", str(RUNNER)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode != 0
    assert "database name must identify a disposable" in (result.stdout + result.stderr)

def _run_seed_guard_with_database_urls(
    tmp_path: Path,
    database_url: str | None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
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
            "DATABASE_URL_SYNC": "postgresql://postgres:secret@localhost:5432/zina_disposable",
            "RUN_LOCAL_SEEDS": "true",
            "ZINA_DEPLOYMENT_ENV": "development",
            "APP_ROOT": str(ROOT),
            "PSQL_MARKER": str(psql_marker),
            "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
        }
    )
    if database_url is None:
        env.pop("DATABASE_URL", None)
    else:
        env["DATABASE_URL"] = database_url

    result = subprocess.run(
        ["sh", str(RUNNER)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result, psql_marker


@pytest.mark.parametrize(
    ("database_url", "expected_message"),
    [
        (
            "postgresql+asyncpg://postgres:secret@localhost:5432/other_database",
            "must target the same host, port, and database",
        ),
        (
            "postgresql+asyncpg://postgres:secret@127.0.0.1:5432/zina_disposable",
            "must target the same host, port, and database",
        ),
        (
            "postgresql+asyncpg://postgres:secret@localhost:5433/zina_disposable",
            "must target the same host, port, and database",
        ),
        (
            "postgresql+asyncpg://postgres:secret@localhost:5432/zina_disposable?sslmode=require",
            "DATABASE_URL query parameters/fragments are forbidden",
        ),
        (
            "postgresql+asyncpg://postgres:secret@localhost:5432/zina_disposable#other",
            "DATABASE_URL query parameters/fragments are forbidden",
        ),
    ],
)
def test_local_seed_opt_in_rejects_mismatched_schema_audit_target_before_database_access(
    tmp_path: Path,
    database_url: str,
    expected_message: str,
) -> None:
    result, psql_marker = _run_seed_guard_with_database_urls(tmp_path, database_url)

    assert result.returncode != 0
    assert expected_message in (result.stdout + result.stderr)
    assert not psql_marker.exists(), "URL mismatch reached psql before the guard rejected it"
    assert "secret" not in (result.stdout + result.stderr), "database credentials must not be logged"


def test_local_seed_opt_in_requires_async_schema_audit_url_before_database_access(
    tmp_path: Path,
) -> None:
    result, psql_marker = _run_seed_guard_with_database_urls(tmp_path, None)

    assert result.returncode != 0
    assert "DATABASE_URL is required" in (result.stdout + result.stderr)
    assert not psql_marker.exists(), "missing audit URL reached psql before the guard rejected it"

