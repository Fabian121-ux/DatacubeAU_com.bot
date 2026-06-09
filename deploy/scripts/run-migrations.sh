#!/bin/sh
set -eu

if [ -z "${DATABASE_URL_SYNC:-}" ]; then
  echo "DATABASE_URL_SYNC is required for psql migrations." >&2
  exit 1
fi

psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f /srv/app/bot_core/migrations/001_init.sql
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f /srv/app/bot_core/migrations/002_expand_v1.sql
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f /srv/app/bot_core/migrations/003_assistant_layer.sql
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f /srv/app/bot_core/migrations/004_nextgen_intelligence.sql
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f /srv/app/bot_core/seeds/001_local_seed.sql
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f /srv/app/bot_core/seeds/002_default_config.sql
