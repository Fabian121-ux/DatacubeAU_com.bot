# Zina Production Hardening Release

Status: independently releasable safety work, split out of the view-once/private-media
track so it can reach `main` without shipping unfinished media foundations.

This release contains **no** view-once feature, **no** private media storage, **no**
retention, and **no** AI media processing. It adds no migrations: the chain still ends at
`029_p0_outbound_authority.sql`, exactly as on `main`.

"Proven" below means local regressions exercise the behaviour with mocked transports. No
real WAHA send, session reconnect, or live WhatsApp message was performed in this track.

## What this release contains

### Ingress safety

- **Status, channel, and broadcast surfaces are never routed.** `status@broadcast`,
  `*@newsletter`, and `*@broadcast` events arrive as ordinary `message` events and were
  previously normalized as DMs, so they could enter reply planning. They are now rejected at
  the canonical webhook before the durable idempotency claim and before any routing side
  effect.
- **Exact WAHA session binding on every message event.** Session validation previously ran
  only when `fromMe` was true, so an event from a stale or foreign WAHA session reached
  persistence, routing, and reply planning with only the shared webhook secret as
  protection. The check is now unconditional and still precedes the idempotency claim, so a
  rejected event leaves no receipt and cannot suppress a later legitimate delivery of the
  same message ID.

### Outbound authority

- **Media identity is bound into the authority hash.** `authority_content_hash()` commits to
  the exact media locator, kind, and caption in addition to the message text. Previously the
  hash covered only `message_text`, so an approval granted for one attachment also authorized
  delivery of a different one. Text-only rows keep their original digest byte-for-byte, so
  approvals stamped before this change remain valid.
- **Broadcast rows are explicitly non-authoritative.** `_queue_broadcast` stamps
  `delivery_policy: unauthorized_broadcast`, which the final fence rejects by name for every
  non-owner recipient. Previously these rows carried no metadata at all and were blocked only
  as a side effect of that absence.

### Outbound media correctness

- **One canonical producer boundary.** `OutboundMediaMetadataService` validates the media
  locator scheme, length, and traversal, canonicalizes producer kind aliases, derives a MIME
  when the producer omits one, and rejects kind/MIME conflicts and unsafe filenames. The
  router applies it before the queue row is created, so the internet service's hidden
  `__media_*` keys can no longer act as a parallel media protocol, and the authority hash
  binds a validated locator. This is normalization, not authorization: rejected media only
  drops the attachment, and the text reply still passes the unchanged approval fence.
- **Typed WAHA adapters.** `send_image`, `send_video`, `send_voice`, and `send_file` post to
  their exact endpoints with a validated MIME and are single-attempt (`retry_safe=False`).
- **Media-type-aware dispatch after the P0 fence.** `OutboundMediaDispatchService` runs only
  after the final authorization fence and the outbound safety limits have already allowed a
  row. It selects one exact operation or fails closed with zero WAHA calls. It can only
  narrow behaviour and is never an authorization mechanism. This prevents video and audio
  from being delivered through the image endpoint. Legacy untyped rows keep their existing
  image-only behaviour and caption fallback.

### Test isolation

- Per-test cleanup is single-sourced and now also covers `admin_accounts`, `audit_logs`,
  `bot_config`, and the migration-owned tables that have no ORM model. Leaked rows previously
  caused unrelated failures: a committed `admin_accounts` row broke command-control tests on
  a unique constraint, and a leaked `inbound_webhook_receipts` row made a later test's
  webhook look like a duplicate and silently suppressed routing.

## What this release deliberately excludes

- `.vv` / `.vvopen` command handler and its Command Center catalog entry
- `ViewOnceCapabilityService` classification
- migrations `030_view_once_media_metadata.sql` and `031_view_once_command_catalog.sql`
- `PrivateMediaArtifact` metadata or private byte storage
- persistent view-once retention and `.vvretain`
- AI image/audio/video processing and derived artifacts

No view-once or deleted-message recovery capability is claimed or exposed. No command is
registered that lacks a working handler. Retention does not exist in this release, so there
is nothing to disable.

These remain on `automation/view-once-media-pipeline` (PR #41), which stays open and can
continue on top of this release.

## Operational invariant: WAHA session binding

`payload.session` must equal the configured `WAHA_SESSION_NAME`. Surrounding whitespace from
the transport is trimmed, but the comparison is **case-sensitive**: `DEFAULT` does not match
`default`. A missing session also fails closed, because the active WAHA build populates
`session` on every webhook (`populateSessionInfo()` in `core/abc/manager.abc.js`) and the
`WAHAWebhook` DTO marks it `required: true`.

Webhook authentication and session binding answer different questions. Authentication proves
the caller knows the shared secret; session binding proves the event belongs to this Zina WAHA
session. Both are required.

**Operational consequence:** if the deployed WAHA session is renamed without updating
`WAHA_SESSION_NAME`, all inbound events fail closed and are logged as `unexpected_session`.
This is intentional for a security boundary, but the two values must be changed together.

## Deployment notes

- No migration is added, so no schema change is required to deploy this release.
- No configuration change is required, provided `WAHA_SESSION_NAME` already matches the
  deployed WAHA session name.
- Existing durable outbound approvals remain valid: text-only authority digests are
  unchanged.

## Live testing status

This release makes controlled live testing *safer*; it does not by itself prove live
readiness. No media type has been verified end to end against the live WAHA engine or a real
WhatsApp account, and no live test should be run without explicit owner approval.
