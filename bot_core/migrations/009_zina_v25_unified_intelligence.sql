BEGIN;

ALTER TABLE outbound_queue
  ADD COLUMN IF NOT EXISTS media_url TEXT,
  ADD COLUMN IF NOT EXISTS media_type VARCHAR(40),
  ADD COLUMN IF NOT EXISTS media_caption TEXT;

CREATE TABLE IF NOT EXISTS group_metadata (
  id                  BIGSERIAL PRIMARY KEY,
  chat_id             VARCHAR(120) NOT NULL UNIQUE,
  group_name          VARCHAR(220),
  community_name      VARCHAR(220),
  owner_name          VARCHAR(180),
  purpose             TEXT,
  notes               TEXT,
  tags                JSONB,
  first_seen          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen           TIMESTAMPTZ,
  member_count        INTEGER,
  participants_count  INTEGER,
  description         TEXT,
  bot_present         BOOLEAN,
  source              VARCHAR(40) NOT NULL DEFAULT 'local',
  live_metadata_json  JSONB,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_group_metadata_chat_id ON group_metadata (chat_id);
CREATE INDEX IF NOT EXISTS idx_group_metadata_community ON group_metadata (community_name);
CREATE INDEX IF NOT EXISTS idx_group_metadata_source ON group_metadata (source);

UPDATE bot_config
SET config_value = 'searxng', updated_at = NOW()
WHERE config_key = 'internet_provider' AND config_value IN ('', 'brave', 'tavily');

INSERT INTO bot_config (config_key, config_value) VALUES
  ('internet_provider', 'searxng')
ON CONFLICT (config_key) DO NOTHING;

COMMIT;
