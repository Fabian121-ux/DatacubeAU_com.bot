-- Foundational data model for the Intelligent Outbound Message Library (roadmap
-- Phase 17, docs/ZINA_IMPLEMENTATION_ROADMAP.md). This is the "WHAT COULD ZINA SAY?"
-- layer only: reusable message sets, their approved template variants, and an
-- analytics/audit trail of which variant was selected for which contact and why.
--
-- This migration is purely additive and does NOT change outbound delivery behavior:
-- no producer or delivery path is wired to these tables yet, `outbound_queue` and
-- `scheduled_actions` are untouched, and the existing P0 final authorization fence in
-- `background_workers.py::_delivery_authorized` is not modified. Selecting a variant
-- here never grants send authority by itself (see docs/ZINA_IMPLEMENTATION_ROADMAP.md
-- Phase 17, "Authority separation").

CREATE TABLE IF NOT EXISTS outbound_message_sets (
    id BIGSERIAL PRIMARY KEY,
    set_key VARCHAR(120) NOT NULL UNIQUE,
    name VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(80) NOT NULL,
    purpose TEXT NULL,
    channel VARCHAR(40) NOT NULL DEFAULT 'whatsapp',
    primary_language VARCHAR(20) NULL,
    selection_strategy VARCHAR(40) NOT NULL DEFAULT 'deterministic_score',
    created_by VARCHAR(120) NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMPTZ NULL,
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_outbound_message_sets_category_active
    ON outbound_message_sets (category)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS outbound_message_variants (
    id BIGSERIAL PRIMARY KEY,
    message_set_id BIGINT NOT NULL REFERENCES outbound_message_sets(id) ON DELETE CASCADE,
    label VARCHAR(40) NOT NULL,
    template_body TEXT NOT NULL,
    required_variables JSONB NULL,
    optional_variables JSONB NULL,
    media_locator TEXT NULL,
    media_kind VARCHAR(40) NULL,
    media_mime VARCHAR(160) NULL,
    media_caption TEXT NULL,
    language VARCHAR(20) NULL,
    tags JSONB NULL,
    weight INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMPTZ NULL,
    deleted_at TIMESTAMPTZ NULL,

    CONSTRAINT ck_outbound_message_variants_weight_positive CHECK (weight >= 1)
);

-- A label is only unique among a set's *active* variants, so a deleted "A" can be
-- superseded by a new "A" without renaming anything.
CREATE UNIQUE INDEX IF NOT EXISTS ux_outbound_message_variants_set_label
    ON outbound_message_variants (message_set_id, label)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_outbound_message_variants_set_eligible
    ON outbound_message_variants (message_set_id, status)
    WHERE deleted_at IS NULL AND is_enabled = true;

-- Analytics/audit trail only. Never consulted by the delivery fence; this table
-- cannot grant, imply, or record outbound authority by itself.
CREATE TABLE IF NOT EXISTS outbound_variant_usage (
    id BIGSERIAL PRIMARY KEY,
    contact_id BIGINT NULL REFERENCES contacts(id) ON DELETE SET NULL,
    message_set_id BIGINT NOT NULL REFERENCES outbound_message_sets(id) ON DELETE CASCADE,
    variant_id BIGINT NOT NULL REFERENCES outbound_message_variants(id) ON DELETE CASCADE,
    outbound_queue_id BIGINT NULL REFERENCES outbound_queue(id) ON DELETE SET NULL,
    selection_score NUMERIC NULL,
    selection_reason TEXT NULL,
    source_automation VARCHAR(120) NULL,
    send_result VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_outbound_variant_usage_contact_set
    ON outbound_variant_usage (contact_id, message_set_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_outbound_variant_usage_variant
    ON outbound_variant_usage (variant_id, created_at DESC);
