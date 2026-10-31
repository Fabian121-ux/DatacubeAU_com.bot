BEGIN;

ALTER TABLE contacts
    ADD COLUMN IF NOT EXISTS whatsapp_phone VARCHAR(80),
    ADD COLUMN IF NOT EXISTS normalized_phone VARCHAR(80),
    ADD COLUMN IF NOT EXISTS chat_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS waha_contact_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS waha_participant_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS push_name VARCHAR(180),
    ADD COLUMN IF NOT EXISTS contact_name VARCHAR(180),
    ADD COLUMN IF NOT EXISTS profile_image_url TEXT,
    ADD COLUMN IF NOT EXISTS identity_source VARCHAR(40),
    ADD COLUMN IF NOT EXISTS identity_json JSONB,
    ADD COLUMN IF NOT EXISTS is_name_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_contacts_normalized_phone ON contacts (normalized_phone);
CREATE INDEX IF NOT EXISTS idx_contacts_last_active_at ON contacts (last_active_at DESC);

ALTER TABLE faq_entries
    ADD COLUMN IF NOT EXISTS source_id VARCHAR(120) NOT NULL DEFAULT 'core_faq',
    ADD COLUMN IF NOT EXISTS source_name VARCHAR(220),
    ADD COLUMN IF NOT EXISTS source_version VARCHAR(80) NOT NULL DEFAULT 'legacy',
    ADD COLUMN IF NOT EXISTS source_hash VARCHAR(80),
    ADD COLUMN IF NOT EXISTS sync_status VARCHAR(40) NOT NULL DEFAULT 'synced',
    ADD COLUMN IF NOT EXISTS last_synchronized_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS category VARCHAR(80) NOT NULL DEFAULT 'General',
    ADD COLUMN IF NOT EXISTS intent VARCHAR(120) NOT NULL DEFAULT 'custom',
    ADD COLUMN IF NOT EXISTS dedupe_key TEXT,
    ADD COLUMN IF NOT EXISTS question_variations JSONB,
    ADD COLUMN IF NOT EXISTS keywords JSONB,
    ADD COLUMN IF NOT EXISTS entities JSONB,
    ADD COLUMN IF NOT EXISTS confidence_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.72,
    ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS success_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS failed_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;

UPDATE faq_entries
SET dedupe_key = normalized_question
WHERE dedupe_key IS NULL OR dedupe_key = '';

CREATE INDEX IF NOT EXISTS idx_faq_entries_source_version
    ON faq_entries (source_id, source_version, is_enabled);

CREATE INDEX IF NOT EXISTS idx_faq_entries_sync_status
    ON faq_entries (sync_status);

CREATE INDEX IF NOT EXISTS idx_faq_entries_dedupe_key
    ON faq_entries (dedupe_key);

UPDATE command_catalog
SET category = 'Admin Commands',
    updated_at = NOW()
WHERE category = 'Owner Commands';

CREATE TABLE IF NOT EXISTS identity_registry (
    id BIGSERIAL PRIMARY KEY,
    registry_key VARCHAR(120) NOT NULL UNIQUE,
    category VARCHAR(80) NOT NULL DEFAULT 'Identity',
    name VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    aliases JSONB,
    keywords JSONB,
    entities JSONB,
    answer TEXT NOT NULL,
    facts_json JSONB,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO identity_registry (
    registry_key,
    category,
    name,
    description,
    aliases,
    keywords,
    entities,
    answer,
    facts_json,
    is_enabled,
    created_at,
    updated_at
) VALUES
(
    'zina',
    'Zina',
    'Zina',
    'Zina is Fabian''s personal AI assistant.',
    '["Zina", "assistant", "you"]',
    '["assistant", "name", "created", "built", "owner"]',
    '["Zina", "Fabian"]',
    'I am Zina, Fabian''s AI assistant.',
    '{"protected": true, "type": "AI assistant"}',
    TRUE,
    NOW(),
    NOW()
),
(
    'fabian',
    'Owner',
    'Fabian',
    'Fabian is the owner and creator Zina assists.',
    '["Fabian", "owner", "creator"]',
    '["owner", "creator", "developer", "builder"]',
    '["Fabian"]',
    'Fabian is the owner and creator I assist.',
    '{"protected": true, "role": "Owner and creator"}',
    TRUE,
    NOW(),
    NOW()
),
(
    'datacube_au',
    'Datacube AU',
    'Datacube AU',
    'Datacube AU is part of Fabian''s AI assistant and automation ecosystem.',
    '["Datacube", "Datacube AU"]',
    '["datacube", "project", "assistant", "automation", "knowledge"]',
    '["Datacube AU", "Fabian"]',
    'Datacube AU is an AI-powered assistant and knowledge automation project created by Fabian.',
    '{"protected": true, "project": true}',
    TRUE,
    NOW(),
    NOW()
),
(
    'zinax',
    'ZinaX',
    'ZinaX',
    'ZinaX is a project in Fabian''s AI assistant ecosystem.',
    '["ZinaX"]',
    '["zinax", "project", "assistant", "automation"]',
    '["ZinaX", "Fabian"]',
    'ZinaX is part of Fabian''s AI assistant and automation ecosystem.',
    '{"protected": true, "project": true}',
    TRUE,
    NOW(),
    NOW()
),
(
    'services',
    'Services',
    'Fabian Services',
    'Fabian builds AI-assisted systems, automation tools, and productivity-focused projects.',
    '["services", "what Fabian offers"]',
    '["services", "automation", "ai", "systems", "productivity"]',
    '["Fabian", "Datacube AU", "Zina"]',
    'Fabian focuses on AI-assisted systems, automation tools, WhatsApp assistant systems, and productivity-focused projects.',
    '{"protected": true}',
    TRUE,
    NOW(),
    NOW()
),
(
    'projects',
    'Projects',
    'Fabian Projects',
    'Fabian''s active ecosystem includes Datacube AU, Zina, ZinaX, and Moxiz Gateway.',
    '["projects", "Fabian projects", "what Fabian is building"]',
    '["projects", "building", "datacube", "zina", "zinax", "moxiz"]',
    '["Fabian", "Datacube AU", "Zina", "ZinaX", "Moxiz Gateway"]',
    'Fabian''s core projects include Datacube AU, Zina, ZinaX, and Moxiz Gateway.',
    '{"protected": true}',
    TRUE,
    NOW(),
    NOW()
),
(
    'skills',
    'Skills',
    'Fabian Skills',
    'Fabian works across AI systems, automation, Python, FastAPI, TypeScript, Docker, cybersecurity, and workflow tooling.',
    '["skills", "Fabian skills", "what Fabian can do"]',
    '["skills", "ai", "python", "fastapi", "typescript", "docker", "cybersecurity", "automation"]',
    '["Fabian"]',
    'Fabian works with AI systems, Python, FastAPI, TypeScript, Node.js, Docker, cybersecurity, and workflow automation.',
    '{"protected": true}',
    TRUE,
    NOW(),
    NOW()
),
(
    'moxiz_gateway',
    'Projects',
    'Moxiz Gateway',
    'Moxiz Gateway is part of Fabian''s broader product and automation ecosystem.',
    '["Moxiz", "Moxiz Gateway"]',
    '["moxiz", "gateway", "project", "automation"]',
    '["Moxiz Gateway", "Fabian"]',
    'Moxiz Gateway is part of Fabian''s broader product and automation ecosystem.',
    '{"protected": true, "project": true}',
    TRUE,
    NOW(),
    NOW()
)
ON CONFLICT (registry_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS admin_accounts (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(180) NOT NULL,
    whatsapp_number VARCHAR(80) NOT NULL,
    normalized_whatsapp_id VARCHAR(120) NOT NULL UNIQUE,
    role VARCHAR(80) NOT NULL DEFAULT 'admin',
    permission_level VARCHAR(40) NOT NULL DEFAULT 'owner',
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_active_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_accounts_single_primary
    ON admin_accounts (is_primary)
    WHERE is_primary IS TRUE AND is_enabled IS TRUE;

CREATE INDEX IF NOT EXISTS idx_admin_accounts_enabled
    ON admin_accounts (is_enabled, permission_level);

DO $$
DECLARE
    owner_ids_text TEXT := '';
BEGIN
    IF to_regclass('public.bot_config') IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'bot_config' AND column_name = 'config_value'
        ) THEN
            EXECUTE 'SELECT config_value FROM bot_config WHERE config_key = $1 LIMIT 1'
            INTO owner_ids_text
            USING 'owner_whatsapp_ids';
        ELSIF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'bot_config' AND column_name = 'value'
        ) THEN
            EXECUTE 'SELECT value FROM bot_config WHERE key = $1 LIMIT 1'
            INTO owner_ids_text
            USING 'owner_whatsapp_ids';
        END IF;
    END IF;

    INSERT INTO admin_accounts (
        name,
        whatsapp_number,
        normalized_whatsapp_id,
        role,
        permission_level,
        is_primary,
        is_enabled,
        created_at,
        updated_at
    )
    SELECT
        CASE WHEN ordinality = 1 THEN 'Primary Admin' ELSE 'Admin ' || ordinality::TEXT END,
        raw_number,
        CASE
            WHEN raw_number LIKE '%@%' THEN lower(raw_number)
            ELSE regexp_replace(raw_number, '[^0-9]', '', 'g') || '@c.us'
        END,
        CASE WHEN ordinality = 1 THEN 'primary_admin' ELSE 'admin' END,
        'owner',
        ordinality = 1,
        TRUE,
        NOW(),
        NOW()
    FROM (
        SELECT trim(ids.value) AS raw_number, ids.ordinality
        FROM regexp_split_to_table(COALESCE(owner_ids_text, ''), '[\s,;]+') WITH ORDINALITY AS ids(value, ordinality)
    ) owner_ids
    WHERE raw_number <> ''
      AND (
          raw_number LIKE '%@%'
          OR regexp_replace(raw_number, '[^0-9]', '', 'g') <> ''
      )
    ON CONFLICT (normalized_whatsapp_id) DO UPDATE
    SET whatsapp_number = EXCLUDED.whatsapp_number,
        updated_at = NOW();
END $$;

COMMIT;
