#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL migration-owner async URL is required}"
: "${DATABASE_URL_SYNC:?DATABASE_URL_SYNC migration-owner sync URL is required}"
: "${DATABASE_URL_RUNTIME:?DATABASE_URL_RUNTIME restricted API URL is required}"
: "${ZINA_RUNTIME_DB_PASSWORD:?ZINA_RUNTIME_DB_PASSWORD is required}"

ZINA_RUNTIME_DB_ROLE="${ZINA_RUNTIME_DB_ROLE:-zina_runtime}"
export ZINA_RUNTIME_DB_ROLE

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

# Reject endpoint/credential mismatches before any role or privilege mutation.
python "$SCRIPT_DIR/validate_runtime_database_urls.py"

# psql reads the runtime password from its environment; it is not interpolated
# into a shell command or printed in deployment logs.
env -u PGUSER -u PGHOSTADDR -u PGPORT -u PGOPTIONS -u PGSERVICE -u PGSERVICEFILE \
  PGOPTIONS='-c search_path=public' \
  psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -q -f "$SCRIPT_DIR/provision-runtime-role.sql"

# Prove that the exact URL destined for the API connects as the restricted role.
python "$SCRIPT_DIR/validate_runtime_database_urls.py" --verify-runtime
