BEGIN;

CREATE TABLE IF NOT EXISTS bot_numbers (
  id BIGSERIAL PRIMARY KEY,
  label VARCHAR(120) NOT NULL UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_sessions (
  id BIGSERIAL PRIMARY KEY,
  bot_number_id BIGINT REFERENCES bot_numbers(id) ON DELETE SET NULL,
  session_name VARCHAR(120) NOT NULL UNIQUE,
  status VARCHAR(40) NOT NULL DEFAULT 'unknown',
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contacts (
  id BIGSERIAL PRIMARY KEY,
  whatsapp_id VARCHAR(64) NOT NULL UNIQUE,
  display_name VARCHAR(180),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  bot_number_id BIGINT REFERENCES bot_numbers(id) ON DELETE SET NULL,
  contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
  chat_id VARCHAR(120) NOT NULL,
  chat_type VARCHAR(20) NOT NULL CHECK (chat_type IN ('dm', 'group')),
  direction VARCHAR(20) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
  message_text TEXT NOT NULL,
  normalized_text TEXT NOT NULL,
  message_type VARCHAR(40) NOT NULL DEFAULT 'text',
  raw_payload_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS group_configs (
  id BIGSERIAL PRIMARY KEY,
  chat_id VARCHAR(120) NOT NULL UNIQUE,
  reply_mode VARCHAR(40) NOT NULL DEFAULT 'mention_only'
    CHECK (reply_mode IN ('mention_only', 'off')),
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  cooldown_seconds INT NOT NULL DEFAULT 45,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dm_configs (
  id BIGSERIAL PRIMARY KEY,
  contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE UNIQUE,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  cooldown_seconds INT NOT NULL DEFAULT 6,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS router_decisions (
  id BIGSERIAL PRIMARY KEY,
  message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  decision_type VARCHAR(40) NOT NULL CHECK (
    decision_type IN (
      'ignore',
      'static_reply',
      'kb_reply',
      'cooldown_block',
      'no_match',
      'ai_reply_light',
      'ai_reply_deep'
    )
  ),
  reason TEXT NOT NULL,
  confidence DOUBLE PRECISION,
  reply_sent BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
  id BIGSERIAL PRIMARY KEY,
  title VARCHAR(220) NOT NULL,
  source_type VARCHAR(40) NOT NULL CHECK (
    source_type IN (
      'architecture',
      'branch_notes',
      'product_docs',
      'faq',
      'support_fix',
      'pricing',
      'policy',
      'chat_summary',
      'admin_note'
    )
  ),
  raw_text TEXT NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  status VARCHAR(40) NOT NULL DEFAULT 'indexing',
  metadata_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  heading VARCHAR(220),
  content TEXT NOT NULL,
  normalized_content TEXT NOT NULL,
  token_estimate INT NOT NULL,
  metadata_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_knowledge_chunk_doc_idx UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS qa_cache (
  id BIGSERIAL PRIMARY KEY,
  normalized_question TEXT NOT NULL UNIQUE,
  answer_text TEXT NOT NULL,
  answer_mode VARCHAR(40) NOT NULL,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  source_json JSONB,
  hit_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_calls (
  id BIGSERIAL PRIMARY KEY,
  message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
  prompt_hash VARCHAR(64) NOT NULL,
  mode VARCHAR(40) NOT NULL,
  model VARCHAR(160) NOT NULL,
  prompt_tokens INT NOT NULL DEFAULT 0,
  completion_tokens INT NOT NULL DEFAULT 0,
  latency_ms INT NOT NULL DEFAULT 0,
  success BOOLEAN NOT NULL DEFAULT FALSE,
  request_json JSONB,
  response_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_sessions (
  id BIGSERIAL PRIMARY KEY,
  chat_id VARCHAR(120) NOT NULL UNIQUE,
  chat_type VARCHAR(20) NOT NULL CHECK (chat_type IN ('dm', 'group')),
  summary TEXT,
  last_intent VARCHAR(120),
  last_message_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  action VARCHAR(120) NOT NULL,
  entity_type VARCHAR(80) NOT NULL,
  entity_id VARCHAR(120),
  details_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages (chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_contact_created ON messages (contact_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_direction_created ON messages (direction, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_normalized_text ON messages (normalized_text);
CREATE INDEX IF NOT EXISTS idx_router_decisions_message_created ON router_decisions (message_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_group_configs_chat_id ON group_configs (chat_id);
CREATE INDEX IF NOT EXISTS idx_dm_configs_contact_id ON dm_configs (contact_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_status_enabled ON knowledge_documents (status, is_enabled, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document_id ON knowledge_chunks (document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_qa_cache_normalized_question ON qa_cache (normalized_question);
CREATE INDEX IF NOT EXISTS idx_ai_calls_message_created ON ai_calls (message_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_chat_id ON conversation_sessions (chat_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs (created_at DESC);

COMMIT;
