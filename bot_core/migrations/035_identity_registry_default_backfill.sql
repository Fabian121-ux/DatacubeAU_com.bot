-- Backfill source/entity_type for default identity rows seeded before migration 033
-- added those columns. ensure_defaults_from_profile() only inserts a default when its
-- registry_key is entirely absent, so an upgraded installation whose defaults were
-- seeded by migrations 010/013 (or an earlier ensure_defaults_from_profile run before
-- 033) keeps NULL source/entity_type forever -- the seeder has no repair path for a
-- row that already exists. This is a one-time, idempotent, additive data backfill:
-- it only fills rows that are still NULL, so any row already assigned a source or
-- entity_type (default or a real admin_dashboard edit) is left untouched.
--
-- Matching by registry_key alone is not enough: an administrator could have edited a
-- default's content through the pre-existing upsert endpoint before migration 033
-- even added this column, in which case source is NULL for that row too, and
-- labeling it "system_default" would misattribute real admin-authored content. Both
-- migrations 010 and 013, and IdentityRegistryService.ensure_defaults_from_profile(),
-- insert every default with created_at and updated_at set to the exact same instant
-- (either the same DEFAULT NOW() evaluation or the same utcnow() call), while
-- upsert_identity_registry's edit path only ever advances updated_at, never
-- created_at. `updated_at = created_at` therefore reliably means "never edited since
-- creation" regardless of how old the row is, so only those rows are backfilled;
-- an edited row (even one edited long before migration 033 existed) is left
-- ambiguous rather than mislabeled.

UPDATE identity_registry
SET source = 'system_default'
WHERE source IS NULL
  AND updated_at = created_at
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
  AND updated_at = created_at
  AND registry_key IN ('zina', 'fabian', 'services', 'datacube_au', 'zinax', 'moxiz_gateway', 'projects', 'skills');
