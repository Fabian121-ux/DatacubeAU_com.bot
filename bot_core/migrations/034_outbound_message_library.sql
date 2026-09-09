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
    deleted_at TIMESTAMPTZ NULL,

    -- Only one strategy is implemented so far (see OutboundMessageLibraryService.
    -- ALLOWED_SELECTION_STRATEGIES); expanding this set is deliberately the trigger
    -- for that future work, not something a raw insert should be able to bypass.
    CONSTRAINT ck_outbound_message_sets_selection_strategy
        CHECK (selection_strategy IN ('deterministic_score'))
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

    CONSTRAINT ck_outbound_message_variants_weight_bounded CHECK (weight BETWEEN 1 AND 100),
    CONSTRAINT ck_outbound_message_variants_status CHECK (status IN ('draft', 'approved'))
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
-- cannot grant, imply, or record outbound authority by itself. message_set_id and
-- variant_id are ON DELETE SET NULL rather than CASCADE, so a future hard-delete of
-- library content (maintenance/retention cleanup) cannot erase the historical
-- selection-reason/send-result audit trail this table exists to preserve.
CREATE TABLE IF NOT EXISTS outbound_variant_usage (
    id BIGSERIAL PRIMARY KEY,
    contact_id BIGINT NULL REFERENCES contacts(id) ON DELETE SET NULL,
    message_set_id BIGINT NULL REFERENCES outbound_message_sets(id) ON DELETE SET NULL,
    variant_id BIGINT NULL REFERENCES outbound_message_variants(id) ON DELETE SET NULL,
    outbound_queue_id BIGINT NULL REFERENCES outbound_queue(id) ON DELETE SET NULL,
    selection_score DOUBLE PRECISION NULL,
    selection_reason TEXT NULL,
    source_automation VARCHAR(120) NULL,
    send_result VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_outbound_variant_usage_send_result
        CHECK (send_result IN ('pending', 'sent', 'failed', 'blocked'))
);

CREATE INDEX IF NOT EXISTS ix_outbound_variant_usage_contact_set
    ON outbound_variant_usage (contact_id, message_set_id, created_at DESC);

-- A retried record_variant_usage() call for the same queued delivery must not be
-- counted twice: without this, a producer retry after a transient failure (or a
-- duplicate selection-engine call) would insert a second independent usage row for
-- one outbound_queue row, double-counting the selection and leaving only one of the
-- duplicates eligible to receive its final send result via update_usage_send_result().
CREATE UNIQUE INDEX IF NOT EXISTS ux_outbound_variant_usage_queue
    ON outbound_variant_usage (outbound_queue_id)
    WHERE outbound_queue_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_outbound_variant_usage_variant
    ON outbound_variant_usage (variant_id, created_at DESC);

-- The service already rejects a NaN/infinite selection_score before insert, but a
-- seed, maintenance script, or direct insert has no equivalent guard. "x = x" is
-- false only for NaN; the range comparison excludes +/-Infinity.
ALTER TABLE outbound_variant_usage
    ADD CONSTRAINT ck_outbound_variant_usage_selection_score_finite
    CHECK (
        selection_score IS NULL OR (
            selection_score = selection_score
            AND selection_score > '-Infinity'::double precision
            AND selection_score < 'Infinity'::double precision
        )
    );

-- id alone is already unique (primary key); this composite exists purely so the
-- foreign key below has something to reference.
ALTER TABLE outbound_message_variants
    ADD CONSTRAINT ux_outbound_message_variants_id_set UNIQUE (id, message_set_id);

-- Enforces at the database level what record_variant_usage() already checks in
-- code: variant_id must actually belong to message_set_id, so a direct insert,
-- seed, or maintenance script can no longer pair a real variant with a
-- message_set_id belonging to a *different* set and corrupt per-set/per-variant
-- analytics grouping. MATCH SIMPLE (Postgres's default for a composite FK) means
-- this is only checked when both columns are non-null, so a hard-deleted
-- variant/set -- which SET NULL applies to both columns of together, since this
-- is one composite constraint -- doesn't trip it.
ALTER TABLE outbound_variant_usage
    ADD CONSTRAINT fk_outbound_variant_usage_variant_set
    FOREIGN KEY (variant_id, message_set_id)
    REFERENCES outbound_message_variants (id, message_set_id)
    ON DELETE SET NULL;
