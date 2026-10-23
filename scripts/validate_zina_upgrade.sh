#!/usr/bin/env bash
# CI-only simulation of an installed database upgraded from schema 001-033.
# Uses a separate ephemeral PostgreSQL database; never points at production.
set -euo pipefail

: "${UPGRADE_DATABASE_URL_SYNC:?UPGRADE_DATABASE_URL_SYNC is required}"
: "${UPGRADE_DATABASE_URL:?UPGRADE_DATABASE_URL is required}"

APP_ROOT="${APP_ROOT:-$PWD}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-$APP_ROOT/bot_core/migrations}"
SEEDS_DIR="${SEEDS_DIR:-$APP_ROOT/bot_core/seeds}"

cleanup() {
  psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'zina_upgrade_test' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
  psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -c "DROP DATABASE IF EXISTS zina_upgrade_test;" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Build the pre-upgrade schema exactly as the deployment would have it before 034.
for migration in "$MIGRATIONS_DIR"/*.sql; do
  name="${migration##*/}"
  version="${name%%_*}"
  version_num=$((10#$version))
  if (( version_num >= 34 )); then
    continue
  fi
  psql "$UPGRADE_DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -f "$migration"
done

# Simulate an installed database: seed data already exists and the migration ledger
# records the exact checksums through 033. The deployment runner must skip those
# checksummed migrations, apply only 034-037, reapply seeds safely, then pass schema audit.
for seed in "$SEEDS_DIR"/*.sql; do
  psql "$UPGRADE_DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -f "$seed"
done

psql "$UPGRADE_DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -c "
CREATE TABLE schema_migrations (
  version TEXT PRIMARY KEY,
  checksum TEXT NOT NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);"

for migration in "$MIGRATIONS_DIR"/*.sql; do
  name="${migration##*/}"
  version="${name%%_*}"
  version_num=$((10#$version))
  if (( version_num >= 34 )); then
    continue
  fi
  checksum="$(sha256sum "$migration" | awk '{print $1}')"
  psql "$UPGRADE_DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -c \
    "INSERT INTO schema_migrations (version, checksum) VALUES ('$name', '$checksum');"
done

DATABASE_URL_SYNC="$UPGRADE_DATABASE_URL_SYNC" \
DATABASE_URL="$UPGRADE_DATABASE_URL" \
APP_ROOT="$APP_ROOT" MIGRATIONS_DIR="$MIGRATIONS_DIR" SEEDS_DIR="$SEEDS_DIR" \
  sh "$APP_ROOT/deploy/scripts/run-migrations.sh"

recorded="$(psql "$UPGRADE_DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "SELECT COUNT(*) FROM schema_migrations;")"
if [ "$recorded" != "37" ]; then
  echo "Expected 37 checksummed migrations after upgrade; found $recorded." >&2
  exit 1
fi
for version in 034_private_media_artifact_source_identity.sql 035_identity_registry_default_backfill.sql 036_outbound_message_library.sql 037_outbound_message_set_key_registry.sql; do
  count="$(psql "$UPGRADE_DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "SELECT COUNT(*) FROM schema_migrations WHERE version = '$version';")"
  if [ "$count" != "1" ]; then
    echo "Migration ledger missing expected version: $version" >&2
    exit 1
  fi
done

echo "Installed-database upgrade 033 -> 037 passed; all 37 migration checksums recorded."
