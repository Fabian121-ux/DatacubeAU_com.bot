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
  ZINA_DEPLOYMENT_ENV=development \
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
UPDATE reply_rules
SET response_text = 'operator-customized /help response',
    is_enabled = FALSE,
    priority = 7,
    updated_at = NOW()
WHERE keyword = '/help'
  AND match_mode = 'exact'
  AND chat_type_filter IS NULL;
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
printf '%s\n' "$second_output" | grep -Fq "Skipping recorded migration 001_init.sql" || {
  echo "The second deployment did not skip its recorded migration checksum." >&2
  exit 1
}
printf '%s\n' "$second_output" | grep -Fq "Applying seed 002_default_config.sql" || {
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

# The default reply-rule seed must be idempotent too. ReplyRule has no unique
# constraint, so bare ON CONFLICT DO NOTHING would silently duplicate every rule
# on each deployment. A same-key operator edit must also survive a redeploy.
default_rule_keys="('help'), ('/help'), ('commands'), ('status'), ('/status'), ('ping'), ('/start'), ('hi'), ('hello'), ('hey'), ('good morning'), ('good afternoon'), ('good evening'), ('who are you'), ('what is your name'), ('what is datacube au')"
missing_default_keys="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "
WITH expected(keyword) AS (VALUES $default_rule_keys)
SELECT e.keyword
FROM expected AS e
WHERE NOT EXISTS (
  SELECT 1 FROM reply_rules AS r WHERE r.keyword = e.keyword
)
ORDER BY e.keyword;
")"
if [ -n "$missing_default_keys" ]; then
  echo "Default reply-rule seed omitted expected keys: $missing_default_keys" >&2
  exit 1
fi

default_rule_counts_before="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "
SELECT COUNT(*)::text || ':' || COUNT(DISTINCT keyword)::text
FROM reply_rules
WHERE keyword IN (
  'help', '/help', 'commands', 'status', '/status', 'ping', '/start',
  'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
  'who are you', 'what is your name', 'what is datacube au'
)
  AND match_mode = 'exact'
  AND chat_type_filter IS NULL;
")"
before_rows="${default_rule_counts_before%%:*}"
before_keys="${default_rule_counts_before##*:}"
if [ -z "$before_rows" ] || [ "$before_rows" != "$before_keys" ]; then
  echo "Default reply-rule keys are duplicated before redeploy: $default_rule_counts_before" >&2
  exit 1
fi

custom_reply_state="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "
SELECT response_text || ':' || is_enabled::text || ':' || priority::text
FROM reply_rules
WHERE keyword = '/help'
  AND match_mode = 'exact'
  AND chat_type_filter IS NULL;
")"
if [ "$custom_reply_state" != "operator-customized /help response:false:7" ]; then
  echo "Default redeploy overwrote operator-edited reply rule: $custom_reply_state" >&2
  exit 1
fi

default_rule_counts_after="$(psql "$TEST_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "
SELECT COUNT(*)::text || ':' || COUNT(DISTINCT keyword)::text
FROM reply_rules
WHERE keyword IN (
  'help', '/help', 'commands', 'status', '/status', 'ping', '/start',
  'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
  'who are you', 'what is your name', 'what is datacube au'
)
  AND match_mode = 'exact'
  AND chat_type_filter IS NULL;
")"
if [ "$default_rule_counts_after" != "$default_rule_counts_before" ]; then
  echo "Default reply-rule seed changed row counts on redeploy: before=$default_rule_counts_before after=$default_rule_counts_after" >&2
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
