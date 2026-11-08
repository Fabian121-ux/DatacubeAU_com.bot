from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "deploy" / "scripts" / "run-migrations.sh"


def test_psql_calls_ignore_inherited_libpq_target_overrides(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    env_marker = tmp_path / "psql-environment.txt"
    fake_psql = fake_bin / "psql"
    fake_psql.write_text(
        """#!/bin/sh
{
  printf 'PGUSER=%s|' "${PGUSER-<unset>}"
  printf 'PGHOSTADDR=%s|' "${PGHOSTADDR-<unset>}"
  printf 'PGPORT=%s|' "${PGPORT-<unset>}"
  printf 'PGOPTIONS=%s|' "${PGOPTIONS-<unset>}"
  printf 'PGSERVICE=%s|' "${PGSERVICE-<unset>}"
  printf 'PGSERVICEFILE=%s|' "${PGSERVICEFILE-<unset>}"
  search_path_public=0
  for arg in "$@"; do
    if [ "$arg" = "SET search_path TO public" ]; then
      search_path_public=1
    fi
  done
  printf 'search_path_public=%s|' "$search_path_public"
  printf '%s' '---|'
} >> "$PSQL_ENV_MARKER"
calls=$(grep -o -- '---|' "$PSQL_ENV_MARKER" | wc -l)
if [ "$calls" -ge 2 ]; then exit 23; fi
exit 0
""",
        encoding="utf-8",
    )
    fake_psql.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            # Deliberately omit :port so libpq would otherwise consult PGPORT.
            "DATABASE_URL_SYNC": "postgresql://postgres:secret@localhost/zina_disposable",
            "DATABASE_URL": "postgresql+asyncpg://postgres:secret@localhost/zina_disposable",
            "RUN_LOCAL_SEEDS": "false",
            "ZINA_DEPLOYMENT_ENV": "production",
            "APP_ROOT": str(ROOT),
            "PSQL_ENV_MARKER": str(env_marker),
            "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
            "PGUSER": "untrusted-role",
            "PGHOSTADDR": "203.0.113.77",
            "PGPORT": "6543",
            "PGOPTIONS": "-csearch_path=untrusted_schema",
            "PGSERVICE": "untrusted-service",
            "PGSERVICEFILE": str(tmp_path / "untrusted-pg_service.conf"),
        }
    )
    result = subprocess.run(
        ["sh", str(RUNNER)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    # The fake client succeeds for CREATE TABLE, then fails on the first scalar
    # query. This exercises both psql_cmd() and sql_scalar() without a DB connection.
    assert result.returncode != 0
    captured = env_marker.read_text(encoding="utf-8")
    assert captured.count("---|") == 2
    for variable in ("PGUSER", "PGHOSTADDR", "PGPORT", "PGOPTIONS", "PGSERVICE", "PGSERVICEFILE"):
        assert captured.count(f"{variable}=<unset>|") == 2
    assert captured.count("search_path_public=1|") == 2, (
        "every psql session must pin the audited public schema despite server-side defaults"
    )
    assert "secret" not in (result.stdout + result.stderr)
