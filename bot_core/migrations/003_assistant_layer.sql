BEGIN;

-- =============================================================
-- 003: Assistant intelligence layer
--   • reply_rules    – admin-editable keyword→response pairs
--   • user_memory    – per-user persistent memory / preferences
--   • bot_config     – key-value runtime configuration store
--   • extends router_decisions constraint for new decision types
-- =============================================================

-- 1. Reply Rules -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS reply_rules (
  id          BIGSERIAL PRIMARY KEY,
  keyword     VARCHAR(220) NOT NULL,
  response_text TEXT       NOT NULL,
  match_mode  VARCHAR(20) NOT NULL DEFAULT 'contains'
              CHECK (match_mode IN ('exact', 'contains', 'startswith')),
  chat_type_filter VARCHAR(20) DEFAULT NULL
              CHECK (chat_type_filter IS NULL OR chat_type_filter IN ('dm', 'group')),
  is_enabled  BOOLEAN     NOT NULL DEFAULT TRUE,
  priority    INT         NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reply_rules_enabled_priority
  ON reply_rules (is_enabled, priority DESC);

-- 2. User Memory -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_memory (
  id                  BIGSERIAL PRIMARY KEY,
  contact_id          BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE UNIQUE,
  user_name           VARCHAR(180),
  preferences         TEXT,
  context_notes       TEXT,
  onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_memory_contact ON user_memory (contact_id);

-- 3. Bot Config (key-value) ------------------------------------------------
CREATE TABLE IF NOT EXISTS bot_config (
  id          BIGSERIAL PRIMARY KEY,
  config_key  VARCHAR(120) NOT NULL UNIQUE,
  config_value TEXT       NOT NULL DEFAULT '',
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_config_key ON bot_config (config_key);

-- 4. Extend router_decisions decision_type constraint ----------------------
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'router_decisions_decision_type_check'
  ) THEN
    ALTER TABLE router_decisions DROP CONSTRAINT router_decisions_decision_type_check;
  END IF;
END $$;

ALTER TABLE router_decisions
  ADD CONSTRAINT router_decisions_decision_type_check CHECK (
    decision_type IN (
      'ignore',
      'static_reply',
      'kb_reply',
      'cooldown_block',
      'no_match',
      'ai_reply_light',
      'ai_reply_deep',
      'reply_rule',
      'memory_onboard',
      'rate_limited'
    )
  );

COMMIT;
