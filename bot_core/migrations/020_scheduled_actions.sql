CREATE TABLE IF NOT EXISTS scheduled_actions (
    id BIGSERIAL PRIMARY KEY,
    action_type VARCHAR(120) NOT NULL,
    target_contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
    target_chat_id VARCHAR(120) NOT NULL,
    payload_json JSONB NOT NULL,
    timezone VARCHAR(80) NOT NULL DEFAULT 'UTC',
    scheduled_for TIMESTAMPTZ NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'scheduled',
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    source_message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
    requested_by_contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
    outbound_queue_id BIGINT REFERENCES outbound_queue(id) ON DELETE SET NULL,
    idempotency_key VARCHAR(160) NOT NULL UNIQUE,
    last_error TEXT,
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    executed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    CONSTRAINT scheduled_actions_status_check CHECK (status IN ('scheduled', 'paused', 'executing', 'queued', 'completed', 'cancelled', 'failed')),
    CONSTRAINT scheduled_actions_action_type_check CHECK (action_type IN ('whatsapp.send_message'))
);

CREATE INDEX IF NOT EXISTS idx_scheduled_actions_due
    ON scheduled_actions(status, is_enabled, scheduled_for, id);

CREATE INDEX IF NOT EXISTS idx_scheduled_actions_target
    ON scheduled_actions(target_contact_id, scheduled_for DESC);

CREATE INDEX IF NOT EXISTS idx_scheduled_actions_chat
    ON scheduled_actions(target_chat_id, scheduled_for DESC);
