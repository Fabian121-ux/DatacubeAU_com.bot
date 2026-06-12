BEGIN;

CREATE TABLE IF NOT EXISTS forced_reply_targets (
  id                    BIGSERIAL PRIMARY KEY,
  target_contact_id      BIGINT REFERENCES contacts(id) ON DELETE CASCADE,
  target_whatsapp_id     VARCHAR(120) NOT NULL UNIQUE,
  created_by_contact_id  BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
  is_enabled             BOOLEAN NOT NULL DEFAULT TRUE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_forced_reply_targets_contact ON forced_reply_targets (target_contact_id);
CREATE INDEX IF NOT EXISTS idx_forced_reply_targets_whatsapp ON forced_reply_targets (target_whatsapp_id);

CREATE TABLE IF NOT EXISTS user_triggers (
  id                       BIGSERIAL PRIMARY KEY,
  target_contact_id         BIGINT REFERENCES contacts(id) ON DELETE CASCADE,
  target_whatsapp_id        VARCHAR(120) NOT NULL,
  trigger_text              TEXT NOT NULL,
  normalized_trigger_text   TEXT NOT NULL,
  response_text             TEXT NOT NULL,
  created_by_contact_id     BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
  is_enabled                BOOLEAN NOT NULL DEFAULT TRUE,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_triggers_contact ON user_triggers (target_contact_id);
CREATE INDEX IF NOT EXISTS idx_user_triggers_whatsapp ON user_triggers (target_whatsapp_id);

CREATE TABLE IF NOT EXISTS feedback_reviews (
  id                  BIGSERIAL PRIMARY KEY,
  contact_id           BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
  sender_whatsapp_id   VARCHAR(120) NOT NULL,
  rating              INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment             TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_reviews_created_at ON feedback_reviews (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_reviews_contact ON feedback_reviews (contact_id);

INSERT INTO bot_config (config_key, config_value) VALUES
  ('bot_enabled', 'true'),
  ('maintenance_mode', 'false'),
  ('owner_whatsapp_ids', ''),
  ('group_default_reply_mode', 'mention_only')
ON CONFLICT (config_key) DO NOTHING;

COMMIT;
