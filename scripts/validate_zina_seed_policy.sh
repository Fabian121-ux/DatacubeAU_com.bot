#!/usr/bin/env bash
# CI-only regression for the production migration runner's local-fixture seed policy.
# This creates/drops only a uniquely named database on the disposable Actions PostgreSQL service.
set -euo pipefail

if [ "${GITHUB_ACTIONS:-}" != "true" ]; then
  echo "Refusing seed-policy validation outside GitHub Actions." >&2
  exit 1
fi
: "${DATABASE_URL_SYNC:?DATABASE_URL_SYNC is required}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

url_info="$(python - "${DATABASE_URL_SYNC}" "${GITHUB_RUN_ID:-}" "${GITHUB_RUN_ATTEMPT:-}" <<'PY'
import sys
from urllib.parse import urlsplit, urlunsplit

value, run_id, attempt = sys.argv[1:]
parsed = urlsplit(value)
try:
    host = parsed.hostname
    port = parsed.port
except ValueError as exc:
    raise SystemExit("Refusing seed-policy validation: malformed PostgreSQL URL.")

database = parsed.path.lstrip("/")
if parsed.scheme != "postgresql":
    raise SystemExit("Refusing seed-policy validation: expected a synchronous PostgreSQL URL.")
if host not in {"localhost", "127.0.0.1", "::1"} or database != "datacube_bot_test":
    raise SystemExit("Refusing seed-policy validation: URL must target local datacube_bot_test.")
if port not in {None, 5432} or parsed.query or parsed.fragment:
    raise SystemExit("Refusing seed-policy validation: alternate ports, query parameters, and fragments are forbidden.")
if not run_id.isdecimal() or not attempt.isdecimal():
    raise SystemExit("Refusing seed-policy validation: GitHub run identifiers are required.")

name = f"zina_seed_policy_{run_id}_{attempt}"
print(name)
print(urlunsplit(parsed._replace(path=f"/{name}")))
print(urlunsplit(parsed._replace(scheme="postgresql+asyncpg", path=f"/{name}")))
PY
)" || exit 1

TEST_DB="$(printf '%s\n' "$url_info" | sed -n '1p')"
TEST_URL_SYNC="$(printf '%s\n' "$url_info" | sed -n '2p')"
TEST_URL_ASYNC="$(printf '%s\n' "$url_info" | sed -n '3p')"

cleanup() {
  if [ -n "${TEST_DB:-}" ]; then
    psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -c \
      "DROP DATABASE IF EXISTS \"$TEST_DB\" WITH (FORCE)" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -c \
  "DROP DATABASE IF EXISTS \"$TEST_DB\" WITH (FORCE)" >/dev/null
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -c \
  "CREATE DATABASE \"$TEST_DB\"" >/dev/null

run_runner() {
  local local_seed_mode="$1"
  DATABASE_URL_SYNC="$TEST_URL_SYNC" \
  DATABASE_URL="$TEST_URL_ASYNC" \
  APP_ROOT="$ROOT" \
  RUN_LOCAL_SEEDS="$local_seed_mode" \
    sh "$ROOT/deploy/scripts/run-migrations.sh"
}

first_output=""
if ! first_output="$(run_runner false 2>&1)"; then
  printf '%s\n' "$first_output" >&2
  exit 1
fi
printf '%s\n' "$first_output"
printf '%s\n' "$first_output" | grep -Fq "Skipping local-only seed 001_local_seed.sql" || {
  echo "The initial deployment did not explicitly skip the local fixture seed." >&2
  exit 1
}

local_contact_count="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc \
  "SELECT COUNT(*) FROM contacts WHERE whatsapp_id = '234000000000@c.us';")"
local_group_count="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc \
  "SELECT COUNT(*) FROM group_configs WHERE chat_id = '120363000000000000@g.us';")"
if [ "$local_contact_count" != "0" ] || [ "$local_group_count" != "0" ]; then
  echo "Local fixture rows were inserted during a default deployment." >&2
  exit 1
fi

# Simulate an older installation that already has the local fixture rows.
# Editing them between deploys must survive the runner's default path.
psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -f "$ROOT/bot_core/seeds/001_local_seed.sql" >/dev/null
psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -c "
UPDATE dm_configs
SET is_enabled = FALSE, cooldown_seconds = 91, updated_at = NOW()
WHERE contact_id = (SELECT id FROM contacts WHERE whatsapp_id = '234000000000@c.us');
UPDATE group_configs
SET reply_mode = 'off', is_enabled = FALSE, cooldown_seconds = 91, updated_at = NOW()
WHERE chat_id = '120363000000000000@g.us';
" >/dev/null

second_output=""
if ! second_output="$(run_runner false 2>&1)"; then
  printf '%s\n' "$second_output" >&2
  exit 1
fi
printf '%s\n' "$second_output"
printf '%s\n' "$second_output" | grep -Fq "Skipping local-only seed 001_local_seed.sql" || {
  echo "The second default deployment did not skip the local fixture seed." >&2
  exit 1
}

# Explicitly prove recorded migrations are checksum-skipped while the safe default
# configuration seed is still re-applied on each runner invocation.
printf '%s\\n' "$second_output" | grep -Fq "Skipping recorded migration 001_init.sql" || {
  echo "The second deployment did not skip its recorded migration checksum." >&2
  exit 1
}
printf '%s\\n' "$second_output" | grep -Fq "Applying seed 002_default_config.sql" || {
  echo "The second deployment did not re-run the default configuration seed." >&2
  exit 1
}

dm_state="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "
SELECT is_enabled::text || ':' || cooldown_seconds::text
FROM dm_configs
WHERE contact_id = (SELECT id FROM contacts WHERE whatsapp_id = '234000000000@c.us');
")"
group_state="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "
SELECT reply_mode || ':' || is_enabled::text || ':' || cooldown_seconds::text
FROM group_configs
WHERE chat_id = '120363000000000000@g.us';
")"
if [ "$dm_state" != "false:91" ]; then
  echo "Default redeploy overwrote edited DM configuration: $dm_state" >&2
  exit 1
fi
if [ "$group_state" != "off:false:91" ]; then
  echo "Default redeploy overwrote edited group configuration: $group_state" >&2
  exit 1
fi

# Explicit opt-in remains available for disposable development environments.
opt_in_output=""
if ! opt_in_output="$(run_runner true 2>&1)"; then
  printf '%s\n' "$opt_in_output" >&2
  exit 1
fi
printf '%s\n' "$opt_in_output"
printf '%s\n' "$opt_in_output" | grep -Fq "Applying seed 001_local_seed.sql" || {
  echo "RUN_LOCAL_SEEDS=true did not apply the local fixture seed." >&2
  exit 1
}

dm_opt_in_state="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "
SELECT is_enabled::text || ':' || cooldown_seconds::text
FROM dm_configs
WHERE contact_id = (SELECT id FROM contacts WHERE whatsapp_id = '234000000000@c.us');
")"
group_opt_in_state="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "
SELECT reply_mode || ':' || is_enabled::text || ':' || cooldown_seconds::text
FROM group_configs
WHERE chat_id = '120363000000000000@g.us';
")"
if [ "$dm_opt_in_state" != "true:6" ] || [ "$group_opt_in_state" != "mention_only:true:45" ]; then
  echo "Explicit local-seed opt-in did not restore the documented fixture values." >&2
  exit 1
fi

echo "Deployment seed-policy regression passed: local fixture seeds are opt-in, default redeploy preserves edits, and explicit opt-in remains functional."
