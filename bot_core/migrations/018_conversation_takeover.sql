CREATE TABLE IF NOT EXISTS conversation_takeovers (
    id BIGSERIAL PRIMARY KEY,
    chat_id VARCHAR(120) NOT NULL UNIQUE,
    state VARCHAR(40) NOT NULL DEFAULT 'fabian_active',
    auto_assist_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    inactivity_seconds INTEGER NOT NULL DEFAULT 120 CHECK (inactivity_seconds >= 5),
    pending_since TIMESTAMPTZ NULL,
    takeover_due_at TIMESTAMPTZ NULL,
    last_inbound_message_id VARCHAR(220) NULL,
    last_owner_message_at TIMESTAMPTZ NULL,
    assisting_since TIMESTAMPTZ NULL,
    handoff_sent_at TIMESTAMPTZ NULL,
    last_transition_reason TEXT NULL,
    metadata_json JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_conversation_takeovers_due
    ON conversation_takeovers (takeover_due_at)
    WHERE state = 'waiting_for_fabian' AND auto_assist_enabled = TRUE;
