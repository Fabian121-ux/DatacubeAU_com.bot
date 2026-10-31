BEGIN;

ALTER TABLE router_decisions
  ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS reply_sent BOOLEAN NOT NULL DEFAULT FALSE;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_constraint
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
      'ai_reply_deep'
    )
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
  normalized_content TEXT NOT NULL DEFAULT '',
  token_estimate INT NOT NULL DEFAULT 0,
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

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_status_enabled ON knowledge_documents (status, is_enabled, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document_id ON knowledge_chunks (document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_qa_cache_normalized_question ON qa_cache (normalized_question);
CREATE INDEX IF NOT EXISTS idx_ai_calls_message_created ON ai_calls (message_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_chat_id ON conversation_sessions (chat_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs (created_at DESC);

COMMIT;
