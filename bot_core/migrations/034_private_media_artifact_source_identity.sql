-- Enforces one PrivateMediaArtifact per exact (source_chat_id, source_message_id) while
-- active. This is required before wiring any producer into the service (roadmap phase 5,
-- docs/VIEW_ONCE_MEDIA_PIPELINE.md): without it, a webhook retry or a repeated `.vv info`
-- / `.vvopen` / `.vv list` observation of the same source message would mint a new opaque
-- artifact identity every time instead of converging on one row, exactly the duplication
-- risk the metadata layer exists to avoid. A deleted artifact is not resurrected by a
-- later observation (the partial index excludes deleted_at IS NOT NULL rows), matching the
-- same idempotent-per-source pattern already used by view_once_media_metadata.
--
-- Replaces the non-unique ix_private_media_artifacts_source index from migration 032 with
-- an equivalent-shape UNIQUE index. Purely additive/constraint-tightening: no column
-- changes, no data migration, and no existing row can violate this (the table has never
-- been written to by any producer yet).

DROP INDEX IF EXISTS ix_private_media_artifacts_source;

CREATE UNIQUE INDEX IF NOT EXISTS ux_private_media_artifacts_source
    ON private_media_artifacts (source_chat_id, source_message_id)
    WHERE deleted_at IS NULL;
