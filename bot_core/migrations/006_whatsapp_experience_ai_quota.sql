BEGIN;

ALTER TABLE user_memory
  ADD COLUMN IF NOT EXISTS global_chat_enabled BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS ai_usage_quotas (
  id          BIGSERIAL PRIMARY KEY,
  contact_id  BIGINT NOT NULL UNIQUE REFERENCES contacts(id) ON DELETE CASCADE,
  usage_count INTEGER NOT NULL DEFAULT 0,
  reset_time  TIMESTAMPTZ NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_quotas_reset ON ai_usage_quotas (reset_time);

CREATE TABLE IF NOT EXISTS ai_usage_events (
  id                BIGSERIAL PRIMARY KEY,
  contact_id        BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  ai_call_id        BIGINT REFERENCES ai_calls(id) ON DELETE SET NULL,
  model             VARCHAR(160) NOT NULL,
  mode              VARCHAR(40) NOT NULL,
  prompt_tokens     INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens      INTEGER NOT NULL DEFAULT 0,
  response_source   VARCHAR(40) NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_events_contact_time ON ai_usage_events (contact_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_events_created_at ON ai_usage_events (created_at DESC);

INSERT INTO bot_config (config_key, config_value) VALUES
  ('ai_quota_per_user_daily', '5'),
  ('global_chat_enabled', 'true'),
  ('typing_delay_enabled', 'true'),
  ('min_typing_delay_seconds', '1'),
  ('max_typing_delay_seconds', '6'),
  ('show_source_badges', 'true'),
  ('show_context_badges', 'true'),
  ('enable_signature_style', 'true'),
  ('experience_source_badges_enabled', 'true'),
  ('experience_context_indicators_enabled', 'true'),
  ('experience_typing_presence_enabled', 'false'),
  ('experience_send_thinking_messages', 'false')
ON CONFLICT (config_key) DO NOTHING;

COMMIT;
