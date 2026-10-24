#!/bin/sh
set -eu

if [ -z "${DATABASE_URL_SYNC:-}" ]; then
  echo "DATABASE_URL_SYNC is required for psql migrations." >&2
  exit 1
fi

# Local fixture identities must never be rewritten by a normal production deploy.
# RUN_LOCAL_SEEDS is an explicit opt-in for disposable development/test environments.
RUN_LOCAL_SEEDS="${RUN_LOCAL_SEEDS:-false}"
case "$RUN_LOCAL_SEEDS" in
  true|false) ;;
  *)
    echo "RUN_LOCAL_SEEDS must be exactly 'true' or 'false'." >&2
    exit 1
    ;;
esac

# The production Compose migration service sets this marker explicitly. Even if
# RUN_LOCAL_SEEDS is accidentally added to .env.production, fixture upserts fail
# closed unless the operator explicitly overrides the marker for a dev/test run.
if [ "$RUN_LOCAL_SEEDS" = "true" ]; then
  case "${ZINA_DEPLOYMENT_ENV:-}" in
    development|test) ;;
    *)
      echo "RUN_LOCAL_SEEDS=true requires ZINA_DEPLOYMENT_ENV=development or test." >&2
      exit 1
      ;;
  esac
fi

APP_ROOT="${APP_ROOT:-/srv/app}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-$APP_ROOT/bot_core/migrations}"
SEEDS_DIR="${SEEDS_DIR:-$APP_ROOT/bot_core/seeds}"

psql_cmd() {
  psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X "$@"
}

sql_scalar() {
  psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -X -Atc "$1"
}

table_exists() {
  sql_scalar "SELECT to_regclass('public.$1') IS NOT NULL;"
}

column_exists() {
  sql_scalar "SELECT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = '$1'
      AND column_name = '$2'
  );"
}

migration_satisfied() {
  case "$1" in
    001_init.sql)
      [ "$(table_exists contacts)" = "t" ] && [ "$(table_exists messages)" = "t" ]
      ;;
    002_expand_v1.sql)
      [ "$(table_exists qa_cache)" = "t" ] &&
      [ "$(table_exists ai_calls)" = "t" ] &&
      [ "$(column_exists router_decisions confidence)" = "t" ] &&
      [ "$(column_exists router_decisions reply_sent)" = "t" ]
      ;;
    003_assistant_layer.sql)
      [ "$(table_exists reply_rules)" = "t" ] &&
      [ "$(table_exists user_memory)" = "t" ] &&
      [ "$(table_exists bot_config)" = "t" ]
      ;;
    004_nextgen_intelligence.sql)
      [ "$(table_exists faq_entries)" = "t" ] &&
      [ "$(table_exists outbound_queue)" = "t" ] &&
      [ "$(table_exists waha_outages)" = "t" ] &&
      [ "$(column_exists user_memory profession)" = "t" ]
      ;;
    005_personal_relationship_memory.sql)
      [ "$(table_exists conversation_timeline)" = "t" ] &&
      [ "$(table_exists conversation_summaries)" = "t" ] &&
      [ "$(column_exists user_memory display_name)" = "t" ]
      ;;
    006_whatsapp_experience_ai_quota.sql)
      [ "$(table_exists ai_usage_quotas)" = "t" ] &&
      [ "$(table_exists ai_usage_events)" = "t" ] &&
      [ "$(column_exists user_memory global_chat_enabled)" = "t" ]
      ;;
    007_owner_command_engine.sql)
      [ "$(table_exists forced_reply_targets)" = "t" ] &&
      [ "$(table_exists user_triggers)" = "t" ] &&
      [ "$(table_exists feedback_reviews)" = "t" ]
      ;;
    008_internet_services_engine.sql)
      [ "$(table_exists internet_cache)" = "t" ] &&
      [ "$(table_exists internet_usage_events)" = "t" ]
      ;;
    009_zina_v25_unified_intelligence.sql)
      [ "$(table_exists group_metadata)" = "t" ] &&
      [ "$(column_exists outbound_queue media_url)" = "t" ]
      ;;
    *)
      return 1
      ;;
  esac
}

psql_cmd -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
  version    TEXT PRIMARY KEY,
  checksum   TEXT NOT NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"

for file in "$MIGRATIONS_DIR"/*.sql; do
  version="$(basename "$file")"
  checksum="$(sha256sum "$file" | awk '{print $1}')"
  recorded_checksum="$(sql_scalar "SELECT checksum FROM schema_migrations WHERE version = '$version';")"

  if [ -n "$recorded_checksum" ]; then
    if [ "$recorded_checksum" != "$checksum" ]; then
      echo "Migration checksum mismatch for $version" >&2
      echo "Recorded: $recorded_checksum" >&2
      echo "Current:  $checksum" >&2
      exit 1
    fi
    echo "Skipping recorded migration $version"
    continue
  fi

  if migration_satisfied "$version"; then
    echo "Baselining already-applied migration $version"
    psql_cmd -c "INSERT INTO schema_migrations (version, checksum) VALUES ('$version', '$checksum');"
    continue
  fi

  echo "Applying migration $version"
  psql_cmd -f "$file"
  psql_cmd -c "INSERT INTO schema_migrations (version, checksum) VALUES ('$version', '$checksum');"
done

for seed in "$SEEDS_DIR"/*.sql; do
  [ -f "$seed" ] || continue
  seed_name="$(basename "$seed")"

  case "$seed_name" in
    *_local_seed.sql)
      if [ "$RUN_LOCAL_SEEDS" != "true" ]; then
        echo "Skipping local-only seed $seed_name (set RUN_LOCAL_SEEDS=true to opt in)"
        continue
      fi
      ;;
  esac

  echo "Applying seed $seed_name"
  psql_cmd -f "$seed"
done

cd "$APP_ROOT/bot_core"
python scripts/schema_audit.py
