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

-- Durable snapshots of contact_id/message_set_id/variant_id as they were at
-- INSERT time -- deliberately plain columns with no foreign key, so a supported
-- hard-delete (which nulls the live columns above via ON DELETE SET NULL) can
-- never touch them. record_variant_usage()'s idempotency check compares against
-- these, not the live nullable columns: a null live column can't reliably prove
-- "same selection" vs. "erased selection", and treating it as a wildcard let a
-- genuinely different later selection silently claim the same outbound_queue_id
-- (found across three review rounds before this fix). ADD COLUMN IF NOT EXISTS,
-- not a CREATE TABLE edit: safe to re-run against a database where this table
-- already exists without these columns.
ALTER TABLE outbound_variant_usage ADD COLUMN IF NOT EXISTS original_message_set_id BIGINT NULL;
ALTER TABLE outbound_variant_usage ADD COLUMN IF NOT EXISTS original_variant_id BIGINT NULL;
ALTER TABLE outbound_variant_usage ADD COLUMN IF NOT EXISTS original_contact_id BIGINT NULL;

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
--
-- Guarded by a catalog existence check, not a bare ALTER TABLE: this migration
-- runs outside a transaction (see deploy/scripts/run-migrations.sh, which records
-- the migration only after the whole file succeeds), so if deployment is
-- interrupted after this ADD CONSTRAINT commits but before the file finishes, the
-- next startup re-runs the file from the top and a bare ALTER would fail
-- immediately on "constraint already exists" -- leaving deployment unable to
-- self-recover. The IF NOT EXISTS forms below (CREATE INDEX, CREATE OR REPLACE
-- FUNCTION, DROP TRIGGER IF EXISTS) are already safe to re-run for the same
-- reason; ADD CONSTRAINT has no such clause in PostgreSQL, so it needs this
-- explicit guard instead.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_outbound_variant_usage_selection_score_finite'
    ) THEN
        ALTER TABLE outbound_variant_usage
            ADD CONSTRAINT ck_outbound_variant_usage_selection_score_finite
            CHECK (
                selection_score IS NULL OR (
                    selection_score = selection_score
                    AND selection_score > '-Infinity'::double precision
                    AND selection_score < 'Infinity'::double precision
                )
            );
    END IF;
END;
$$;

-- Enforces at the database level what record_variant_usage() already checks in
-- code: variant_id must actually belong to message_set_id, so a direct insert,
-- seed, or maintenance script can no longer pair a real variant with a
-- message_set_id belonging to a *different* set and corrupt per-set/per-variant
-- analytics grouping.
--
-- A trigger, not a composite foreign key: a composite FK's single ON DELETE
-- action applies to the whole tuple, so hard-deleting *only* a variant would also
-- null message_set_id on its usage rows even though the parent set is untouched
-- and still valid -- discarding real, still-correct set attribution from
-- historical analytics. A trigger enforces the pairing on write only, leaving the
-- two independent single-column foreign keys below to null exactly (and only)
-- the column whose own referenced row was actually deleted. ERRCODE 23514
-- (check_violation) makes this classify as an IntegrityError the same way a real
-- constraint violation would, for callers/tests that catch IntegrityError.
CREATE OR REPLACE FUNCTION zina_check_outbound_variant_usage_set_pairing()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- A fresh row must name both a set and a variant: record_variant_usage()
    -- always supplies both, and a seed/maintenance/direct-ORM insert supplying
    -- only one would produce a usage row that can never be attributed to a
    -- real selection. Only INSERT is checked here -- the two independent
    -- single-column ON DELETE SET NULL foreign keys below legitimately clear
    -- one field at a time via an UPDATE when the referenced set/variant is
    -- hard-deleted, and that referential action must keep working.
    IF TG_OP = 'INSERT' THEN
        IF NEW.variant_id IS NULL OR NEW.message_set_id IS NULL THEN
            RAISE EXCEPTION
                'outbound_variant_usage requires both variant_id and message_set_id on insert'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    IF NEW.variant_id IS NOT NULL AND NEW.message_set_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM outbound_message_variants
            WHERE id = NEW.variant_id AND message_set_id = NEW.message_set_id
        ) THEN
            RAISE EXCEPTION
                'outbound_variant_usage.variant_id % does not belong to message_set_id %',
                NEW.variant_id, NEW.message_set_id
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_outbound_variant_usage_check_set_pairing ON outbound_variant_usage;
CREATE TRIGGER trg_outbound_variant_usage_check_set_pairing
BEFORE INSERT OR UPDATE OF variant_id, message_set_id ON outbound_variant_usage
FOR EACH ROW
EXECUTE FUNCTION zina_check_outbound_variant_usage_set_pairing();
