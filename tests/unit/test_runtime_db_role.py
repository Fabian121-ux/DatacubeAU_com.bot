from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import asyncpg
from sqlalchemy.engine import make_url
import pytest


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "deploy" / "scripts" / "validate_runtime_database_urls.py"
PROVISIONER = ROOT / "deploy" / "scripts" / "provision-runtime-role.sh"


def _runtime_url(owner_url: str, role: str, password: str) -> str:
    return make_url(owner_url).set(
        drivername="postgresql+asyncpg",
        username=role,
        password=password,
    ).render_as_string(hide_password=False)


def _valid_env() -> dict[str, str]:
    owner_async = "postgresql+asyncpg://migrator:mig%40pass%3Aword@db.example:5432/zina"
    owner_sync = "postgresql://migrator:mig%40pass%3Aword@db.example:5432/zina"
    runtime_password = "run@time:secret/with spaces"
    runtime_url = (
        "postgresql+asyncpg://zina_runtime:run%40time%3Asecret%2Fwith%20spaces"
        "@db.example:5432/zina"
    )
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": owner_async,
        "DATABASE_URL_SYNC": owner_sync,
        "DATABASE_URL_RUNTIME": runtime_url,
        "ZINA_RUNTIME_DB_ROLE": "zina_runtime",
        "ZINA_RUNTIME_DB_PASSWORD": runtime_password,
    })
    return env


def test_runtime_database_url_preflight_accepts_matching_distinct_roles():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        env=_valid_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"DATABASE_URL_RUNTIME": "postgresql+asyncpg://zina_runtime:secret@other-host:5432/zina"}, "same PostgreSQL endpoint"),
        ({"DATABASE_URL_RUNTIME": "postgresql+asyncpg://migrator:secret@db.example:5432/zina"}, "distinct ZINA_RUNTIME_DB_ROLE"),
        ({"DATABASE_URL_RUNTIME": "postgresql+asyncpg://zina_runtime:secret@db.example:5432/zina?options=-csearch_path%3Dtenant"}, "query or fragment"),
        ({"DATABASE_URL_RUNTIME": "postgresql+asyncpg://zina_runtime:secret@db1,db2:5432/zina"}, "exactly one PostgreSQL host"),
        ({"ZINA_RUNTIME_DB_ROLE": "postgres"}, "distinct ZINA_RUNTIME_DB_ROLE"),
    ],
)
def test_runtime_database_url_preflight_rejects_unsafe_configuration(change, message):
    env = _valid_env()
    env.update(change)
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert message in result.stderr
    assert "run@time:secret" not in result.stderr
    assert "mig@pass" not in result.stderr


def _compose_service_block(compose: str, name: str) -> str:
    markers = [
        "  postgres:\\n",
        "  api:\\n",
        "  waha:\\n",
        "  nginx:\\n",
        "  migrate:\\n",
        "\\nvolumes:\\n",
    ]
    start = compose.index(f"  {name}:\\n")
    ends = [compose.find(marker, start + 1) for marker in markers if compose.find(marker, start + 1) >= 0]
    return compose[start:min(ends) if ends else len(compose)]


def test_compose_uses_service_specific_environment_allowlists():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    postgres = _compose_service_block(compose, "postgres")
    api = _compose_service_block(compose, "api")
    waha = _compose_service_block(compose, "waha")
    migrate = _compose_service_block(compose, "migrate")

    for block in (postgres, api, waha, migrate):
        assert "env_file:" not in block

    assert "DATABASE_URL: ${DATABASE_URL_RUNTIME" in api
    assert "DATABASE_URL_SYNC" not in api
    assert "ZINA_RUNTIME_DB_PASSWORD" not in api
    assert "DATABASE_URL" not in postgres
    assert "DATABASE_URL" not in waha
    assert "ADMIN_API_TOKEN" not in waha
    assert "OPENROUTER_API_KEY" not in waha
    assert "DATABASE_URL_SYNC" in migrate
    assert "ZINA_RUNTIME_DB_PASSWORD" in migrate


@pytest.mark.asyncio
async def test_runtime_role_cannot_mutate_or_disable_consent_history():
    owner_sync = os.environ.get("DATABASE_URL_SYNC")
    owner_async = os.environ.get("DATABASE_URL")
    if not owner_sync or not owner_async or not shutil.which("psql"):
        pytest.skip("migration-owner URLs and psql are required for the PostgreSQL role integration test")

    role = "zina_runtime_test"
    password = "runtime-test@password:with/slashes"
    runtime_url = _runtime_url(owner_sync, role, password)
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": owner_async,
        "DATABASE_URL_SYNC": owner_sync,
        "DATABASE_URL_RUNTIME": runtime_url,
        "ZINA_RUNTIME_DB_ROLE": role,
        "ZINA_RUNTIME_DB_PASSWORD": password,
    })

    provision = subprocess.run(
        ["sh", str(PROVISIONER)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert provision.returncode == 0, provision.stderr

    admin = await asyncpg.connect(dsn=owner_sync)
    runtime = await asyncpg.connect(dsn=runtime_url.replace("postgresql+asyncpg://", "postgresql://", 1))
    transaction = runtime.transaction()
    try:
        owner = await admin.fetchval(
            """
            SELECT owner.rolname
            FROM pg_class relation
            JOIN pg_roles owner ON owner.oid = relation.relowner
            WHERE relation.oid = 'public.contact_messaging_consent_events'::regclass
            """
        )
        assert owner != role

        role_state = await admin.fetchrow(
            """
            SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolinherit,
                   rolreplication, rolbypassrls
            FROM pg_roles
            WHERE rolname = $1
            """,
            role,
        )
        assert role_state is not None
        assert role_state["rolcanlogin"] is True
        assert not any(role_state[key] for key in (
            "rolsuper", "rolcreatedb", "rolcreaterole", "rolinherit",
            "rolreplication", "rolbypassrls",
        ))
        memberships = await admin.fetchval(
            "SELECT count(*) FROM pg_auth_members WHERE member = (SELECT oid FROM pg_roles WHERE rolname = $1)",
            role,
        )
        assert memberships == 0

        await transaction.start()
        inserted = await runtime.fetchrow(
            """
            INSERT INTO contact_messaging_consent_events (
                exact_chat_id, event_type, actor_type, evidence_ref
            )
            VALUES ($1, 'granted', 'owner', 'runtime-role-regression')
            RETURNING id
            """,
            f"runtime-role-{uuid.uuid4().hex}@c.us",
        )
        assert inserted is not None
        visible = await runtime.fetchval(
            "SELECT count(*) FROM contact_messaging_consent_events WHERE id = $1",
            inserted["id"],
        )
        assert visible == 1

        statements = [
            "UPDATE contact_messaging_consent_events SET evidence_ref = 'tampered'",
            "DELETE FROM contact_messaging_consent_events",
            "TRUNCATE TABLE contact_messaging_consent_events",
            "ALTER TABLE contact_messaging_consent_events DISABLE TRIGGER ALL",
            f'SET ROLE "{owner.replace(chr(34), chr(34) + chr(34))}"',
        ]
        for statement in statements:
            savepoint = runtime.transaction()
            await savepoint.start()
            try:
                await runtime.execute(statement)
            except asyncpg.InsufficientPrivilegeError:
                await savepoint.rollback()
            else:
                await savepoint.rollback()
                pytest.fail(f"restricted runtime role unexpectedly executed: {statement}")
    finally:
        if transaction.is_active:
            await transaction.rollback()
        await runtime.close()
        await admin.close()
