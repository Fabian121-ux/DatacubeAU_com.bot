BEGIN;

-- Personal relationship memory profile fields.
ALTER TABLE user_memory
  ADD COLUMN IF NOT EXISTS display_name VARCHAR(180),
  ADD COLUMN IF NOT EXISTS relationship_type VARCHAR(40) NOT NULL DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS personality_notes TEXT,
  ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS last_interaction_at TIMESTAMPTZ;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'user_memory_relationship_type_check'
  ) THEN
    ALTER TABLE user_memory
      ADD CONSTRAINT user_memory_relationship_type_check CHECK (
        relationship_type IN (
          'friend',
          'family',
          'colleague',
          'customer',
          'community_member',
          'unknown'
        )
      );
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_memory_relationship_type ON user_memory (relationship_type);
CREATE INDEX IF NOT EXISTS idx_user_memory_last_interaction ON user_memory (last_interaction_at DESC);

-- Conversation timeline stores important contact-scoped discussion events.
CREATE TABLE IF NOT EXISTS conversation_timeline (
  id               BIGSERIAL PRIMARY KEY,
  contact_id       BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  timestamp        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  topic            VARCHAR(220) NOT NULL,
  summary          TEXT NOT NULL,
  importance_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  source           VARCHAR(40) NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_timeline_contact_time ON conversation_timeline (contact_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_timeline_contact_importance ON conversation_timeline (contact_id, importance_score DESC);

-- Compact summaries are generated at configured message thresholds.
CREATE TABLE IF NOT EXISTS conversation_summaries (
  id            BIGSERIAL PRIMARY KEY,
  contact_id    BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  summary       TEXT NOT NULL,
  topics        JSON,
  message_count INTEGER NOT NULL DEFAULT 0,
  threshold     INTEGER,
  source        VARCHAR(40) NOT NULL DEFAULT 'threshold_summary',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_contact_time ON conversation_summaries (contact_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_conversation_summaries_contact_threshold
  ON conversation_summaries (contact_id, threshold)
  WHERE threshold IS NOT NULL;

INSERT INTO bot_config (config_key, config_value)
VALUES ('memory_summary_thresholds', '25,50,100')
ON CONFLICT (config_key) DO NOTHING;

-- Extend decision_type check constraint for memory continuation replies.
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
      'faq_reply',
      'cooldown_block',
      'no_match',
      'ai_reply_light',
      'ai_reply_deep',
      'reply_rule',
      'memory_onboard',
      'memory_reply',
      'rate_limited',
      'escalated'
    )
  );

COMMIT;
