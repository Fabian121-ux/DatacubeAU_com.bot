-- Backfill source/entity_type for default identity rows seeded before migration 033
-- added those columns. ensure_defaults_from_profile() only inserts a default when its
-- registry_key is entirely absent, so an upgraded installation whose defaults were
-- seeded by migrations 010/013 (or an earlier ensure_defaults_from_profile run before
-- 033) keeps NULL source/entity_type forever -- the seeder has no repair path for a
-- row that already exists. This is a one-time, idempotent, additive data backfill:
-- it only fills rows that are still NULL, so any row already assigned a source or
-- entity_type (default or a real admin_dashboard edit) is left untouched.

UPDATE identity_registry
SET source = 'system_default'
WHERE source IS NULL
  AND registry_key IN ('zina', 'fabian', 'services', 'datacube_au', 'zinax', 'moxiz_gateway', 'projects', 'skills');

UPDATE identity_registry
SET entity_type = CASE registry_key
    WHEN 'zina' THEN 'assistant'
    WHEN 'fabian' THEN 'person'
    WHEN 'datacube_au' THEN 'project'
    WHEN 'zinax' THEN 'project'
    WHEN 'moxiz_gateway' THEN 'project'
    WHEN 'services' THEN 'meta'
    WHEN 'projects' THEN 'meta'
    WHEN 'skills' THEN 'meta'
END
WHERE entity_type IS NULL
  AND registry_key IN ('zina', 'fabian', 'services', 'datacube_au', 'zinax', 'moxiz_gateway', 'projects', 'skills');
