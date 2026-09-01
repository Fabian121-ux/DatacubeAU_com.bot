BEGIN;

CREATE TABLE IF NOT EXISTS outbound_approvals (
    id BIGSERIAL PRIMARY KEY,
    inbound_message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    outbound_queue_id BIGINT NOT NULL REFERENCES outbound_queue(id) ON DELETE CASCADE,
    target_chat_id VARCHAR(120) NOT NULL,
    content_sha256 VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    approved_by VARCHAR(120),
    approved_at TIMESTAMPTZ,
    consumed_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT outbound_approvals_status_ck CHECK (status IN ('pending', 'approved', 'rejected', 'consumed', 'expired')),
    CONSTRAINT outbound_approvals_hash_ck CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT outbound_approvals_queue_unique UNIQUE (outbound_queue_id)
);

CREATE INDEX IF NOT EXISTS ix_outbound_approvals_pending
    ON outbound_approvals (status, expires_at);
CREATE INDEX IF NOT EXISTS ix_outbound_approvals_inbound
    ON outbound_approvals (inbound_message_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_outbound_approvals_live_inbound
    ON outbound_approvals (inbound_message_id)
    WHERE status IN ('pending', 'approved');

CREATE TABLE IF NOT EXISTS contact_automation_policies (
    id BIGSERIAL PRIMARY KEY,
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    exact_chat_id VARCHAR(120) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT false,
    relationship_context TEXT,
    tone_guidance TEXT,
    allowed_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    prohibited_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    approval_required_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    quiet_hours_json JSONB,
    expires_at TIMESTAMPTZ,
    created_by VARCHAR(120) NOT NULL,
    disabled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT contact_automation_policy_exact_identity_unique UNIQUE (contact_id, exact_chat_id),
    CONSTRAINT contact_automation_policy_allowed_array_ck CHECK (jsonb_typeof(allowed_categories) = 'array'),
    CONSTRAINT contact_automation_policy_prohibited_array_ck CHECK (jsonb_typeof(prohibited_categories) = 'array'),
    CONSTRAINT contact_automation_policy_approval_array_ck CHECK (jsonb_typeof(approval_required_categories) = 'array')
);

CREATE INDEX IF NOT EXISTS ix_contact_automation_policy_active
    ON contact_automation_policies (contact_id, exact_chat_id, enabled, expires_at);

CREATE TABLE IF NOT EXISTS outbound_authorization_audit (
    id BIGSERIAL PRIMARY KEY,
    outbound_queue_id BIGINT REFERENCES outbound_queue(id) ON DELETE SET NULL,
    inbound_message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
    contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
    target_chat_id VARCHAR(120),
    authority_type VARCHAR(40) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    reason VARCHAR(240) NOT NULL,
    details_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT outbound_authorization_audit_decision_ck CHECK (decision IN ('allow', 'deny', 'approve', 'reject', 'consume', 'expire'))
);

CREATE INDEX IF NOT EXISTS ix_outbound_authorization_audit_queue
    ON outbound_authorization_audit (outbound_queue_id, created_at DESC);

COMMIT;
