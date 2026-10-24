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
