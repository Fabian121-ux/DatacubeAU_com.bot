from __future__ import annotations

import os
import re
import sys
from urllib.parse import unquote, urlsplit


def parse_endpoint(value: str, label: str, *, local_seed_mode: bool):
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise SystemExit(
            f"Refusing migration run: {label} has an invalid host or port."
        ) from exc

    allowed_schemes = {"postgresql"} if label == "DATABASE_URL_SYNC" else {
        "postgresql",
        "postgresql+asyncpg",
    }
    if parsed.scheme not in allowed_schemes:
        raise SystemExit(
            f"Refusing migration run: {label} must use an allowed PostgreSQL URL scheme."
        )
    if local_seed_mode and (parsed.query or parsed.fragment):
        raise SystemExit(
            f"Refusing local fixture seeds: {label} query parameters/fragments are forbidden."
        )
    if parsed.fragment:
        raise SystemExit(
            f"Refusing migration run: {label} URL fragments are not valid database targets."
        )
    if not host:
        raise SystemExit(
            f"Refusing migration run: {label} must include a hostname."
        )

    database = unquote(parsed.path.lstrip("/"))
    if not database:
        raise SystemExit(
            f"Refusing migration run: {label} must include a database name."
        )

    # Never compare or print credentials. Query parameters can be valid connection
    # options for normal deployments; local fixture mode deliberately forbids them.
    endpoint = (host.lower().rstrip("."), port if port is not None else 5432, database)
    return parsed, endpoint


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: validate_migration_database_target.py DATABASE_URL_SYNC DATABASE_URL RUN_LOCAL_SEEDS"
        )

    sync_value, audit_value, run_local_seeds = sys.argv[1:4]
    if run_local_seeds not in {"true", "false"}:
        raise SystemExit("RUN_LOCAL_SEEDS must be exactly 'true' or 'false'.")
    local_seed_mode = run_local_seeds == "true"

    if not audit_value:
        if local_seed_mode:
            raise SystemExit(
                "Refusing local fixture seeds: DATABASE_URL is required to verify the schema-audit target."
            )
        # schema_audit.py falls back to DATABASE_URL_SYNC when DATABASE_URL is absent.
        return 0

    sync_parsed, sync_endpoint = parse_endpoint(
        sync_value, "DATABASE_URL_SYNC", local_seed_mode=local_seed_mode
    )
    _, audit_endpoint = parse_endpoint(
        audit_value, "DATABASE_URL", local_seed_mode=local_seed_mode
    )
    if sync_endpoint != audit_endpoint:
        raise SystemExit(
            "Refusing migration run: DATABASE_URL_SYNC and DATABASE_URL must "
            "target the same host, port, and database."
        )

    if not local_seed_mode:
        return 0

    # These additional restrictions apply only when enabling local fixture upserts.
    host = sync_parsed.hostname
    port = sync_parsed.port
    database = sync_endpoint[2]
    if host not in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}:
        raise SystemExit(
            "Refusing local fixture seeds: target host must be local or host.docker.internal."
        )
    if port not in {None, 5432, 5433}:
        raise SystemExit(
            "Refusing local fixture seeds: target port must be 5432 or 5433."
        )
    if host == "host.docker.internal" and port != 5433:
        raise SystemExit(
            "Refusing local fixture seeds: host.docker.internal must use the documented disposable port 5433."
        )

    is_local_disposable = database == "zina_disposable"

    # The CI namespace is not a generic prefix allowlist. Bind it to this exact
    # workflow run/attempt so a misleading name cannot opt in outside Actions or
    # point at another run's database.
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    expected_ci_database = (
        f"zina_seed_policy_{run_id}_{run_attempt}"
        if os.environ.get("GITHUB_ACTIONS") == "true"
        and run_id.isdecimal()
        and run_attempt.isdecimal()
        else ""
    )
    is_current_ci_disposable = bool(
        expected_ci_database
        and re.fullmatch(r"zina_seed_policy_[0-9]+_[0-9]+", database)
        and database == expected_ci_database
    )
    if not (is_local_disposable or is_current_ci_disposable):
        raise SystemExit(
            "Refusing local fixture seeds: database name must identify a disposable "
            "zina_disposable database or this exact GitHub Actions run's "
            "zina_seed_policy_<run_id>_<run_attempt> database."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
