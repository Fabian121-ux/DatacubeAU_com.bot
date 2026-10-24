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

