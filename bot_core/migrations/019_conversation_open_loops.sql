CREATE TABLE IF NOT EXISTS conversation_open_loops (
    id BIGSERIAL PRIMARY KEY,
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    chat_id VARCHAR(120) NOT NULL,
    source_message_id BIGINT NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
    last_message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    loop_type VARCHAR(30) NOT NULL,
    loop_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    resolution_message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
    resolution_reason VARCHAR(120),
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT conversation_open_loops_status_check CHECK (status IN ('open', 'resolved')),
    CONSTRAINT conversation_open_loops_type_check CHECK (loop_type IN ('question', 'request'))
);

CREATE INDEX IF NOT EXISTS idx_conversation_open_loops_contact_status
    ON conversation_open_loops(contact_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_open_loops_chat_status
    ON conversation_open_loops(chat_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_open_loops_last_message
    ON conversation_open_loops(last_message_id);
