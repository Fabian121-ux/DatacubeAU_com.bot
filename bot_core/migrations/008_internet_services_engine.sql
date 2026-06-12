BEGIN;

CREATE TABLE IF NOT EXISTS internet_cache (
  id                BIGSERIAL PRIMARY KEY,
  service           VARCHAR(40) NOT NULL,
  normalized_query  TEXT NOT NULL,
  answer_text       TEXT NOT NULL,
  response_json     JSONB,
  expires_at        TIMESTAMPTZ NOT NULL,
  hit_count         INTEGER NOT NULL DEFAULT 0,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (service, normalized_query)
);

CREATE INDEX IF NOT EXISTS idx_internet_cache_expiry ON internet_cache (expires_at);
CREATE INDEX IF NOT EXISTS idx_internet_cache_service_query ON internet_cache (service, normalized_query);

CREATE TABLE IF NOT EXISTS internet_usage_events (
  id             BIGSERIAL PRIMARY KEY,
  contact_id      BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
  service         VARCHAR(40) NOT NULL,
  query_text      TEXT NOT NULL,
  provider        VARCHAR(40) NOT NULL,
  cache_hit       BOOLEAN NOT NULL DEFAULT FALSE,
  success         BOOLEAN NOT NULL DEFAULT TRUE,
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_internet_usage_contact_time ON internet_usage_events (contact_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_internet_usage_service_time ON internet_usage_events (service, created_at DESC);

INSERT INTO bot_config (config_key, config_value) VALUES
  ('internet_enabled', 'false'),
  ('web_search_enabled', 'false'),
  ('news_enabled', 'false'),
  ('weather_enabled', 'false'),
  ('currency_enabled', 'false'),
  ('youtube_enabled', 'false'),
  ('image_search_enabled', 'false'),
  ('sticker_search_enabled', 'false'),
  ('internet_provider', 'searxng'),
  ('internet_daily_limit_per_user', '25'),
  ('internet_cache_ttl_seconds', '900'),
  ('internet_smart_detection_enabled', 'true')
ON CONFLICT (config_key) DO NOTHING;

COMMIT;
