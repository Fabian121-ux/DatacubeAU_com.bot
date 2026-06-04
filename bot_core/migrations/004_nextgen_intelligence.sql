BEGIN;

-- 1. Extend user_memory with user profile builder columns
ALTER TABLE user_memory
  ADD COLUMN IF NOT EXISTS profession VARCHAR(180),
  ADD COLUMN IF NOT EXISTS interests TEXT,
  ADD COLUMN IF NOT EXISTS projects TEXT,
  ADD COLUMN IF NOT EXISTS goals TEXT,
  ADD COLUMN IF NOT EXISTS communication_style VARCHAR(180),
  ADD COLUMN IF NOT EXISTS relationship VARCHAR(180);

-- 2. Create User Memory Timeline table
CREATE TABLE IF NOT EXISTS user_memory_timeline (
  id           BIGSERIAL PRIMARY KEY,
  contact_id   BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  memory_text  TEXT NOT NULL,
  source       VARCHAR(40) NOT NULL, -- 'onboarding', 'chat_extraction', 'admin'
  confidence   DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_memory_timeline_contact ON user_memory_timeline (contact_id);

-- 3. Create Core FAQ Entries table
CREATE TABLE IF NOT EXISTS faq_entries (
  id           BIGSERIAL PRIMARY KEY,
  question     TEXT NOT NULL,
  normalized_question TEXT NOT NULL UNIQUE,
  answer       TEXT NOT NULL,
  is_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faq_entries_normalized ON faq_entries (normalized_question);

-- 4. Create Outbound Message Queue table
CREATE TABLE IF NOT EXISTS outbound_queue (
  id              BIGSERIAL PRIMARY KEY,
  chat_id         VARCHAR(120) NOT NULL,
  message_text    TEXT NOT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'sending', 'sent', 'failed', 'retrying'
  retry_count     INTEGER NOT NULL DEFAULT 0,
  max_retries     INTEGER NOT NULL DEFAULT 3,
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outbound_queue_status_attempt ON outbound_queue (status, next_attempt_at);

-- 5. Create WAHA Outages table for self-healing status logs
CREATE TABLE IF NOT EXISTS waha_outages (
  id                   BIGSERIAL PRIMARY KEY,
  previous_status      VARCHAR(40),
  current_status       VARCHAR(40),
  reconnect_attempted  BOOLEAN NOT NULL DEFAULT FALSE,
  reconnect_success    BOOLEAN NOT NULL DEFAULT FALSE,
  details_json         JSON,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Extend decision_type check constraint in router_decisions
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
      'rate_limited',
      'escalated'
    )
  );

-- 7. Zina assistant identity/profile defaults.
-- Existing customized config values are preserved.
INSERT INTO bot_config (config_key, config_value)
SELECT
  'owner_bio',
  COALESCE(
    (SELECT config_value FROM bot_config WHERE config_key = 'identity_bio' LIMIT 1),
    'Fabian is a developer, AI systems builder, automation-focused creator, and productivity and cybersecurity enthusiast.'
  )
ON CONFLICT (config_key) DO NOTHING;

INSERT INTO bot_config (config_key, config_value) VALUES
  ('assistant_name', 'Zina'),
  ('assistant_role', 'Fabian''s Personal AI Assistant'),
  ('owner_name', 'Fabian'),
  ('identity_bio', 'Fabian is a developer, AI systems builder, automation-focused creator, and productivity and cybersecurity enthusiast.'),
  ('identity_projects', 'AI systems, automation tools, WhatsApp assistant systems, knowledge and productivity projects. Main active project: Datacube AU.'),
  ('identity_services', 'AI-assisted systems, automation tools, and productivity-focused projects.'),
  ('identity_skills', 'AI, Automation, Cybersecurity, Python, Node.js'),
  ('identity_interests', 'Technology, Productivity, Automation'),
  ('identity_focus', 'Building intelligent WhatsApp assistants'),
  ('identity_style', 'Helpful, concise, and direct')
ON CONFLICT (config_key) DO NOTHING;

COMMIT;
