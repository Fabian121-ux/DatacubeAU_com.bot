-- Migration 017: P0 Security Sprint

-- Add contact_aliases table
CREATE TABLE IF NOT EXISTS contact_aliases (
    id BIGSERIAL PRIMARY KEY,
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    alias_type VARCHAR(40) NOT NULL,
    raw_identifier VARCHAR(120) NOT NULL UNIQUE,
    normalized_identifier VARCHAR(120),
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Add inbound_events table for deduplication
CREATE TABLE IF NOT EXISTS inbound_events (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(40) NOT NULL DEFAULT 'waha',
    session_name VARCHAR(120) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    provider_message_id VARCHAR(120) NOT NULL,
    chat_id VARCHAR(120),
    sender_id VARCHAR(120),
    payload_hash VARCHAR(64) NOT NULL,
    delivery_attempt_count INTEGER NOT NULL DEFAULT 1,
    processing_status VARCHAR(40) NOT NULL DEFAULT 'received',
    processing_error TEXT,
    related_message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
    first_received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_inbound_event UNIQUE (provider, session_name, event_type, provider_message_id)
);

-- Update outbound_queue table
ALTER TABLE outbound_queue ADD COLUMN IF NOT EXISTS waha_message_id VARCHAR(120);
ALTER TABLE outbound_queue ADD COLUMN IF NOT EXISTS payload_hash VARCHAR(64);
