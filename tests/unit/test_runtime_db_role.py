from __future__ import annotations

import os
import re
import secrets
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


def _is_disposable_runtime_role_target(owner_sync: str, environ: dict[str, str]) -> bool:
    """Allow role DDL only against the isolated CI DB or an explicit local test DB."""
    try:
        url = make_url(owner_sync)
    except Exception:
        return False
    host = (url.host or "").lower()
    database = (url.database or "").lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        return False
    if environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return database == "datacube_bot_test"
    return (
        environ.get("ZINA_ALLOW_RUNTIME_ROLE_INTEGRATION_TEST") == "1"
        and database.endswith("_test")
    )


def _runtime_role_integration_enabled(
    owner_sync: str | None,
    owner_async: str | None,
    environ: dict[str, str],
    *,
    psql_available: bool,
) -> bool:
    return bool(
        owner_sync
        and owner_async
        and psql_available
        and _is_disposable_runtime_role_target(owner_sync, environ)
    )


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
        "POSTGRES_USER": "migrator",
        "POSTGRES_PASSWORD": "mig@pass:word",
        "POSTGRES_DB": "zina",
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
    # Match only a top-level Compose service key. A substring search for
    # "  migrate:" also matches the tail of the six-space-indented
    # api.depends_on.migrate key and returns the wrong block.
    service = re.search(rf"(?m)^  {re.escape(name)}:\s*$", compose)
    if service is None:
        raise AssertionError(f"Compose service {name!r} was not found")

    remainder = compose[service.end():]
    next_boundary = re.search(r"(?m)^(?:  [A-Za-z0-9_-]+:|volumes:)\s*$", remainder)
    end = service.end() + next_boundary.start() if next_boundary else len(compose)
    return compose[service.start():end]


def test_compose_service_block_ignores_nested_dependency_keys():
    compose = """services:
  api:
    depends_on:
      migrate:
        condition: service_completed_successfully
  migrate:
    environment:
      DATABASE_URL_SYNC: owner-url

volumes:
  data:
"""
    block = _compose_service_block(compose, "migrate")
    assert "DATABASE_URL_SYNC: owner-url" in block
    assert "condition: service_completed_successfully" not in block


def test_compose_uses_service_specific_environment_allowlists():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    postgres = _compose_service_block(compose, "postgres")
    api = _compose_service_block(compose, "api")
    waha = _compose_service_block(compose, "waha")
    migrate = _compose_service_block(compose, "migrate")
    migration_runner = (ROOT / "deploy" / "scripts" / "run-migrations.sh").read_text(encoding="utf-8")

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
    assert "POSTGRES_USER:" in migrate
    assert "POSTGRES_PASSWORD:" in migrate
    assert "POSTGRES_DB:" in migrate
    assert migration_runner.index("validate_runtime_database_urls.py") < migration_runner.index("psql_cmd -c")


def test_runtime_role_integration_requires_an_approved_disposable_target():
    remote_production = "postgresql://migrator:secret@db.example:5432/production"
    local_production = "postgresql://migrator:secret@localhost:5432/production"
    local_test = "postgresql://migrator:secret@localhost:5432/zina_test"
    ci_test = "postgresql://postgres:postgres@localhost:5432/datacube_bot_test"

    assert not _runtime_role_integration_enabled(
        remote_production, remote_production, {"GITHUB_ACTIONS": "true"}, psql_available=True
    )
    assert not _runtime_role_integration_enabled(
        local_production,
        local_production,
        {"ZINA_ALLOW_RUNTIME_ROLE_INTEGRATION_TEST": "1"},
        psql_available=True,
    )
    assert not _runtime_role_integration_enabled(
        local_test, local_test, {}, psql_available=True
    )
    assert _runtime_role_integration_enabled(
        local_test,
        local_test,
        {"ZINA_ALLOW_RUNTIME_ROLE_INTEGRATION_TEST": "1"},
        psql_available=True,
    )
    assert _runtime_role_integration_enabled(
        ci_test, ci_test, {"GITHUB_ACTIONS": "true"}, psql_available=True
    )
    assert not _runtime_role_integration_enabled(
        ci_test.replace("datacube_bot_test", "production"),
        ci_test.replace("datacube_bot_test", "production"),
        {"GITHUB_ACTIONS": "true"},
        psql_available=True,
    )


@pytest.mark.asyncio
async def test_runtime_role_cannot_mutate_or_disable_consent_history():
    owner_sync = os.environ.get("DATABASE_URL_SYNC")
    owner_async = os.environ.get("DATABASE_URL")
    environ = os.environ.copy()
    if not _runtime_role_integration_enabled(
        owner_sync, owner_async, environ, psql_available=bool(shutil.which("psql"))
    ):
        pytest.skip(
            "runtime-role DDL is restricted to GitHub's disposable datacube_bot_test "
            "database or an explicitly opted-in local *_test database"
        )

    # Unique credentials prevent cross-run collisions; cleanup below always revokes
    # grants/default ACLs and drops the temporary login, including failed provisions.
    role = f"zina_rt_test_{uuid.uuid4().hex}"
    password = secrets.token_urlsafe(32)
    runtime_url = _runtime_url(owner_sync, role, password)
    secondary_role = f"zina_rt_secondary_{uuid.uuid4().hex}"
    secondary_password = secrets.token_urlsafe(32)
    parent_role = f"zina_rt_parent_{uuid.uuid4().hex}"
    owner_parts = make_url(owner_sync)
    env = environ.copy()
    env.update({
        "DATABASE_URL": owner_async,
        "DATABASE_URL_SYNC": owner_sync,
        "DATABASE_URL_RUNTIME": runtime_url,
        "ZINA_RUNTIME_DB_ROLE": role,
        "ZINA_RUNTIME_DB_PASSWORD": password,
        "POSTGRES_USER": owner_parts.username or "",
        "POSTGRES_PASSWORD": owner_parts.password or "",
        "POSTGRES_DB": owner_parts.database or "",
    })

    admin = await asyncpg.connect(dsn=owner_sync)
    runtime = None
    runtime_probe = None
    secondary = None
    transaction = None
    try:
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

        # Seed both pg_auth_members directions. A secondary login granted the
        # runtime role can SET ROLE into its privileges; the runtime login can
        # SET ROLE into a parent role even though it is NOINHERIT. Re-provisioning
        # must remove both edges, not merely prevent automatic inheritance.
        await admin.execute(
            f"CREATE ROLE \"{secondary_role}\" WITH LOGIN PASSWORD '{secondary_password}'"
        )
        await admin.execute(f'CREATE ROLE "{parent_role}" NOLOGIN')
        await admin.execute(f'GRANT "{role}" TO "{secondary_role}"')
        await admin.execute(f'GRANT "{parent_role}" TO "{role}"')

        secondary_dsn = _runtime_url(
            owner_sync, secondary_role, secondary_password
        ).replace("postgresql+asyncpg://", "postgresql://", 1)
        secondary = await asyncpg.connect(dsn=secondary_dsn)
        await secondary.execute(f'SET ROLE "{role}"')
        assert await secondary.fetchval("SELECT current_user") == role
        await secondary.execute("RESET ROLE")
        await secondary.close()
        secondary = None

        runtime_dsn = runtime_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        runtime_probe = await asyncpg.connect(dsn=runtime_dsn)
        await runtime_probe.execute(f'SET ROLE "{parent_role}"')
        assert await runtime_probe.fetchval("SELECT current_user") == parent_role
        await runtime_probe.execute("RESET ROLE")
        await runtime_probe.close()
        runtime_probe = None

        # Re-run the production provisioner after introducing both membership
        # edges. It must revoke them and its own runtime verifier must reject
        # either direction if a future regression leaves one behind.
        reprovision = subprocess.run(
            ["sh", str(PROVISIONER)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert reprovision.returncode == 0, reprovision.stderr

        secondary = await asyncpg.connect(dsn=secondary_dsn)
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await secondary.execute(f'SET ROLE "{role}"')
        await secondary.close()
        secondary = None

        runtime_probe = await asyncpg.connect(dsn=runtime_dsn)
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await runtime_probe.execute(f'SET ROLE "{parent_role}"')
        await runtime_probe.close()
        runtime_probe = None

        memberships = await admin.fetchval(
            """
            SELECT count(*)
            FROM pg_auth_members
            WHERE member = (SELECT oid FROM pg_roles WHERE rolname = $1)
               OR roleid = (SELECT oid FROM pg_roles WHERE rolname = $1)
            """,
            role,
        )
        assert memberships == 0

        runtime = await asyncpg.connect(dsn=runtime_dsn)
        transaction = runtime.transaction()
        await transaction.start()

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

        sequence = await admin.fetchval(
            "SELECT pg_get_serial_sequence('public.contact_messaging_consent_events', 'id')"
        )
        assert sequence
        assert await admin.fetchval(
            "SELECT has_sequence_privilege($1, $2, 'USAGE')", role, sequence
        )
        assert await admin.fetchval(
            "SELECT has_sequence_privilege($1, $2, 'SELECT')", role, sequence
        )
        assert not await admin.fetchval(
            "SELECT has_sequence_privilege($1, $2, 'UPDATE')", role, sequence
        )

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

        sequence_state = await admin.fetchrow(
            "SELECT last_value, is_called FROM public.contact_messaging_consent_events_id_seq"
        )
        savepoint = runtime.transaction()
        await savepoint.start()
        try:
            await runtime.fetchval(
                "SELECT setval($1::regclass, $2, $3)",
                sequence,
                sequence_state["last_value"],
                sequence_state["is_called"],
            )
        except asyncpg.InsufficientPrivilegeError:
            await savepoint.rollback()
        else:
            await savepoint.rollback()
            pytest.fail("restricted runtime role unexpectedly used setval() on consent audit sequence")

        statements = [
            "UPDATE contact_messaging_consent_events SET evidence_ref = 'tampered'",
            "DELETE FROM contact_messaging_consent_events",
            "TRUNCATE TABLE contact_messaging_consent_events",
            "ALTER TABLE contact_messaging_consent_events DISABLE TRIGGER ALL",
            "CREATE TABLE public.zina_runtime_forbidden (id integer)",
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
        if transaction is not None and transaction.is_active:
            await transaction.rollback()
        for connection in (secondary, runtime_probe, runtime):
            if connection is not None:
                await connection.close()
        try:
            secondary_exists = await admin.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)",
                secondary_role,
            )
            parent_exists = await admin.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)",
                parent_role,
            )
            runtime_exists = await admin.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)",
                role,
            )
            if secondary_exists and runtime_exists:
                await admin.execute(f'REVOKE "{role}" FROM "{secondary_role}"')
            if parent_exists and runtime_exists:
                await admin.execute(f'REVOKE "{parent_role}" FROM "{role}"')
            for cleanup_role in (secondary_role, parent_role, role):
                exists = await admin.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)",
                    cleanup_role,
                )
                if exists:
                    await admin.execute(f'DROP OWNED BY "{cleanup_role}"')
                    await admin.execute(f'DROP ROLE "{cleanup_role}"')
            assert not await admin.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)",
                role,
            )
            assert not await admin.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)",
                secondary_role,
            )
            assert not await admin.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)",
                parent_role,
            )
        finally:
            await admin.close()
