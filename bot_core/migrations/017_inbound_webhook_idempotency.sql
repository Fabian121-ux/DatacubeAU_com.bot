CREATE TABLE IF NOT EXISTS inbound_webhook_receipts (
    id BIGSERIAL PRIMARY KEY,
    event_key VARCHAR(512) NOT NULL UNIQUE,
    session_name VARCHAR(120),
    chat_id VARCHAR(120),
    message_id VARCHAR(255),
    status VARCHAR(32) NOT NULL DEFAULT 'processing',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inbound_webhook_receipts_message_id
    ON inbound_webhook_receipts(message_id);

CREATE INDEX IF NOT EXISTS idx_inbound_webhook_receipts_status
    ON inbound_webhook_receipts(status);
