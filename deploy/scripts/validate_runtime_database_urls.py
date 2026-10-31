from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
import os
import re
import sys
from urllib.parse import unquote, urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


@dataclass(frozen=True, slots=True)
class DatabaseTarget:
    host: str
    port: int
    database: str
    username: str
    password: str

    @property
    def endpoint(self) -> tuple[str, int, str]:
        return (self.host, self.port, self.database)


def _parse_target(name: str, value: str) -> DatabaseTarget:
    if not value:
        raise ValueError(f"{name} is required.")
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgresql", "postgresql+asyncpg"}:
        raise ValueError(f"{name} must use a supported PostgreSQL URL scheme.")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{name} must not contain query or fragment overrides.")
    host = unquote(parsed.hostname or "")
    if not host or "," in host:
        raise ValueError(f"{name} must identify exactly one PostgreSQL host.")
    try:
        port = parsed.port or 5432
    except ValueError:
        raise ValueError(f"{name} contains an invalid PostgreSQL port.") from None
    database = unquote(parsed.path.lstrip("/"))
    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    if not database or "/" in database:
        raise ValueError(f"{name} must identify exactly one database.")
    if not username or not password:
        raise ValueError(f"{name} must include an explicit username and password.")
    return DatabaseTarget(host=host.lower(), port=port, database=database, username=username, password=password)


def validate_environment(environ: Mapping[str, str] = os.environ) -> str:
    role = environ.get("ZINA_RUNTIME_DB_ROLE", "zina_runtime")
    if not _ROLE_RE.fullmatch(role):
        raise ValueError("ZINA_RUNTIME_DB_ROLE must be a simple PostgreSQL role identifier.")
    raw_runtime_password = environ.get("ZINA_RUNTIME_DB_PASSWORD", "")
    if not raw_runtime_password:
        raise ValueError("ZINA_RUNTIME_DB_PASSWORD is required.")

    migration_async = _parse_target("DATABASE_URL", environ.get("DATABASE_URL", ""))
    migration_sync = _parse_target("DATABASE_URL_SYNC", environ.get("DATABASE_URL_SYNC", ""))
    runtime = _parse_target("DATABASE_URL_RUNTIME", environ.get("DATABASE_URL_RUNTIME", ""))

    if (
        migration_async.endpoint != migration_sync.endpoint
        or migration_async.username != migration_sync.username
        or migration_async.password != migration_sync.password
    ):
        raise ValueError("DATABASE_URL and DATABASE_URL_SYNC must use the same migration-owner credentials and endpoint.")
    if runtime.endpoint != migration_sync.endpoint:
        raise ValueError("DATABASE_URL_RUNTIME must target the same PostgreSQL endpoint and database as the migration URLs.")
    if runtime.username != role or runtime.username == migration_sync.username:
        raise ValueError("DATABASE_URL_RUNTIME must use the distinct ZINA_RUNTIME_DB_ROLE login.")
    if runtime.password != raw_runtime_password:
        raise ValueError("DATABASE_URL_RUNTIME password must match ZINA_RUNTIME_DB_PASSWORD.")

    postgres_user = environ.get("POSTGRES_USER", "")
    postgres_password = environ.get("POSTGRES_PASSWORD", "")
    postgres_database = environ.get("POSTGRES_DB", "")
    if not postgres_user or not postgres_password or not postgres_database:
        raise ValueError("POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB are required.")
    if (
        migration_sync.username != postgres_user
        or migration_sync.password != postgres_password
        or migration_sync.database != postgres_database
    ):
        raise ValueError("Migration-owner URLs must match the PostgreSQL bootstrap user, password, and database.")
    return role


async def verify_runtime_role(role: str) -> None:
    engine = create_async_engine(os.environ["DATABASE_URL_RUNTIME"], pool_pre_ping=True)
    query = text(
        """
        SELECT
            current_user = :expected_role
            AND r.rolcanlogin
            AND NOT r.rolsuper
            AND NOT r.rolcreatedb
            AND NOT r.rolcreaterole
            AND NOT r.rolinherit
            AND NOT r.rolreplication
            AND NOT r.rolbypassrls
            AND NOT EXISTS (
                SELECT 1 FROM pg_auth_members membership
                WHERE membership.member = r.oid
            )
            AND NOT EXISTS (
                SELECT 1 FROM pg_class relation
                WHERE relation.relowner = r.oid
            )
            AND NOT EXISTS (
                SELECT 1 FROM pg_namespace namespace
                WHERE namespace.nspowner = r.oid
            )
            AND CASE
                WHEN to_regclass('public.contact_messaging_consent_events') IS NULL THEN TRUE
                ELSE
                    has_table_privilege(current_user, to_regclass('public.contact_messaging_consent_events'), 'SELECT')
                    AND has_table_privilege(current_user, to_regclass('public.contact_messaging_consent_events'), 'INSERT')
                    AND NOT has_table_privilege(current_user, to_regclass('public.contact_messaging_consent_events'), 'UPDATE')
                    AND NOT has_table_privilege(current_user, to_regclass('public.contact_messaging_consent_events'), 'DELETE')
                    AND NOT has_table_privilege(current_user, to_regclass('public.contact_messaging_consent_events'), 'TRUNCATE')
                    AND NOT has_table_privilege(current_user, to_regclass('public.contact_messaging_consent_events'), 'REFERENCES')
                    AND NOT has_table_privilege(current_user, to_regclass('public.contact_messaging_consent_events'), 'TRIGGER')
            END
        FROM pg_roles r
        WHERE r.rolname = current_user
        """
    )
    try:
        async with engine.connect() as connection:
            result = await connection.execute(query, {"expected_role": role})
            valid = result.scalar_one_or_none()
        if valid is not True:
            raise RuntimeError("The connected API role does not satisfy the restricted runtime privilege contract.")
    finally:
        await engine.dispose()


def main() -> int:
    try:
        role = validate_environment()
        if "--verify-runtime" in sys.argv[1:]:
            asyncio.run(verify_runtime_role(role))
    except Exception as exc:  # noqa: BLE001 - this is a deployment preflight boundary
        print(f"Runtime database role validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
