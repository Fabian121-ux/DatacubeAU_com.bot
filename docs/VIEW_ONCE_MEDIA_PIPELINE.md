# Zina View-Once and Private Media Pipeline

Status: design/continuity contract for the successor to PR #38 after P0 outbound containment landed on `main`.

## Current proven state

This section describes what is implemented and covered by tests on this branch. Everything
outside it remains design intent. "Proven" here means local regressions exercise the
behaviour with mocked transports; no claim is made about live WhatsApp traffic, because no
real WAHA send or session reconnect has been performed in this track.

### Implemented and tested

- **Media identity is bound into outbound authority.** `OutboundAuthorizationService.authority_content_hash()`
  commits to the exact media locator, kind, and caption in addition to the message text.
  Changing any of them after approval invalidates the existing authority. Text-only rows
  keep their original digest byte-for-byte, so approvals stamped before this change stay
  valid.
- **One canonical outbound media boundary.** `OutboundMediaMetadataService` validates the
  locator scheme/length/traversal, canonicalizes producer kind aliases, derives a MIME when
  the producer omits one, and rejects kind/MIME conflicts and unsafe filenames. The router
  applies it before the queue row is created, so the hidden `__media_*` producer keys never
  reach the queue as a parallel media protocol. Rejecting media only drops the attachment;
  the text reply still passes the unchanged approval fence.
- **Typed WAHA transport adapters.** `send_image`, `send_video`, `send_voice`, and
  `send_file` post to their exact endpoints with a validated MIME, and are single-attempt
  (`retry_safe=False`). Request contracts are covered by mocked tests.
- **Media-type-aware worker dispatch after P0 authorization.** `OutboundMediaDispatchService`
  runs only after the final authorization fence and the outbound safety limits have already
  allowed a row. It selects one exact operation (`image -> send_image`, `video -> send_video`,
  `voice/PTT -> send_voice`, `audio/document/file -> send_file`) or fails closed with zero
  WAHA calls. It can only narrow behaviour and is never an authorization mechanism.
- **Status, channel, and broadcast ingress rejection.** `status@broadcast`, `*@newsletter`,
  and `*@broadcast` surfaces are rejected at the canonical webhook before the durable
  idempotency claim and before any routing side effect, so they can never become a reply
  candidate.
- **Exact WAHA session binding at ingress.** Every message event must belong to the
  configured session (see the operational invariant below).
- **Broadcast rows are explicitly non-authoritative.** `_queue_broadcast` stamps
  `delivery_policy: unauthorized_broadcast`, which the final fence rejects by name for every
  non-owner recipient, instead of relying on absent metadata.
- **Durable duplicate, burst, and final-fence protections.** A PostgreSQL
  `inbound_webhook_receipts` claim keyed on `session:chat:message_id` collapses `message` and
  `message.any` for one source into a single routing path and survives webhook retries and
  restarts. Per-contact burst coalescing, per-contact and global rate/backlog ceilings, and
  duplicate-content suppression bound outbound volume. The Outbound Queue worker independently
  re-authorizes every row immediately before any WAHA call and quarantines uncertain delivery
  outcomes instead of replaying them.

### Not yet production-complete

These are explicitly unfinished. Do not describe them as working.

- **`.vv` / `.vvopen` end-to-end command handler.** View-once *classification* is implemented
  and tested (`ViewOnceCapabilityService`), and migration 031 registers the command in the
  Command Center catalog, but the handler that resolves a quoted source message, fetches the
  capability, and returns media to the OWNER self-DM is not implemented.
- **`PrivateMediaArtifact` byte storage.** No private byte store, no artifact metadata table
  beyond the capability-truthful `view_once_media_metadata` record, no integrity hashing, no
  quotas, no TTL, and no expiry cleanup.
- **Persistent view-once retention.** Not implemented.
- **`.vvretain on`.** Unavailable, and it must remain unavailable until the storage,
  quota, TTL, deletion, disable, audit, and restart-safety requirements below are met.
- **AI image/audio/video processing.** No vision, transcription, frame sampling, or
  `DerivedArtifact` pipeline exists.
- **End-to-end real image/video/audio proof.** Transport contracts and worker dispatch are
  proven only against mocks. No media type has been verified end-to-end against the live
  WAHA engine or a real WhatsApp account.

**Retention remains OFF.** Nothing in this track stores media bytes, and no view-once or
ephemeral media is archived. No claim is made that Zina can recover view-once or deleted
media; only bounded metadata that WAHA actually exposed is retained.

## Operational invariant: WAHA session binding

`payload.session` must equal the configured `WAHA_SESSION_NAME`. Surrounding whitespace from
the transport is trimmed, but the comparison is **case-sensitive**: `DEFAULT` does not match
`default`. A missing session also fails closed, because the active WAHA build populates
`session` on every webhook (`populateSessionInfo()` in `core/abc/manager.abc.js`) and the
`WAHAWebhook` DTO marks it `required: true`.

Webhook authentication and session binding answer different questions. Authentication proves
the caller knows the shared secret; session binding proves the event belongs to this Zina WAHA
session. Both are required.

Operational consequence: if the deployed WAHA session is renamed without updating
`WAHA_SESSION_NAME`, **all inbound events fail closed** and are logged as `unexpected_session`.
This is intentional for a security boundary, but it means the two values must be changed
together.

## Non-negotiable ownership

- WAHA remains the only current production WhatsApp transport.
- FastAPI remains the application boundary.
- PostgreSQL remains authoritative durable state and policy metadata.
- Command Center remains the only command/alias authority.
- Tool Registry plus deterministic Authority Engine owns capability execution.
- Conversation Engine owns takeover.
- Outbound Queue owns delivery and its P0 final authorization fence applies to every media delivery.
- No Baileys production transport is introduced by this track.
- No second command engine, outbound queue, scheduler, memory store, or knowledge store is created.

## Continuity from PR #38

PR #38 exact validated source head `eebb1233106a6ef858bc70c9f48680c6478b3ccb` remains evidence for the OWNER-only `.vv` / `.vvopen` foundation. It must not be merged as-is after P0 because `main` now owns migration 029 and its worker/command paths contain newer outbound authority changes.

The successor port must preserve these established guarantees:

- exact source-message identity; no text matching;
- explicit view-once transport evidence; ordinary media is never promoted merely because it has media;
- conflicting or malformed source IDs/markers/MIME evidence fail closed;
- OWNER-only command authority derived from durable permissions;
- retention OFF by default;
- temporary WAHA file capability has a bounded absolute TTL and is scrubbed after terminal delivery/expiry;
- no raw WAHA payload, base64 media, or private media URL is stored as durable authoritative metadata;
- terminal ephemeral-media queue rows are non-resendable;
- audit records are privacy bounded and redact media capabilities;
- view-once lifecycle is monotonic and deletion tombstones are preserved.

## P0 integration rule

The current `main` Outbound Queue worker independently authorizes a row before any WAHA call, applies non-owner safety limits, changes the row to `sending`, and quarantines uncertain delivery outcomes rather than blindly replaying them. View-once/media work must layer onto this worker; it must not replace or bypass those controls.

The final media path remains:

`authorized capability -> Outbound Queue -> P0 final authorization fence -> safety limits -> media-type dispatch -> WAHA`

No view-once service may call WAHA directly.

## Migration continuity

`main` now owns `029_p0_outbound_authority.sql`.

The PR #38 migrations are therefore remapped in this successor track:

- old `029_view_once_media_metadata.sql` -> successor `030_view_once_media_metadata.sql`
- old `030_view_once_command_catalog.sql` -> successor `031_view_once_command_catalog.sql`

Any later private-artifact migration starts after 031. Migration numbers are never reused for two production meanings.

## Transport capability truth

The legacy generic `send_media()` helper is wired to `/api/sendImage` and is therefore image-only. It is now reached only by legacy untyped rows, which keep their original image-only behaviour and caption fallback. Video and audio are never routed through it.

Current upstream WAHA source exposes separate REST operations for `sendImage`, `sendVideo`, `sendVoice`, and `sendFile`. Explicit typed adapter methods for all four now exist behind the existing WAHA client boundary, and their request contracts are covered by mocked tests. This is **not** evidence that the deployed WAHA image/tag/engine has been live-verified for every media mode: no media type has been exercised end to end against the live engine or the restricted real WhatsApp account.

Media semantics must stay explicit:

- `image` -> `/api/sendImage`
- `video` -> `/api/sendVideo`
- `voice` -> `/api/sendVoice` only when voice-note/PTT semantics are intended
- generic `audio` -> `/api/sendFile` unless the exact transport contract proves a separate appropriate operation
- generic document/file -> `/api/sendFile`

Unknown or conflicting media types fail closed before transport.

## Storage model: capability is not an artifact

The WAHA `waha_media` volume and a temporary `/api/files/...` URL are transport-managed capabilities/cache. They are not Zina's authoritative persistent private-media store.

Persistent storage, when explicitly enabled by the OWNER, will use one Zina-owned Private Media Artifact service with two layers:

1. PostgreSQL metadata and authority: opaque artifact ID, exact source message/contact/chat identifiers, media kind, MIME, byte size, content hash, transport provenance, retention policy, created/observed timestamps, expiry/deletion state, and bounded audit references.
2. Private byte storage: an internal filesystem/object-store implementation behind the artifact service. PostgreSQL stores an opaque internal locator, never a public download URL and never base64 bytes.

The service must support create/read/delete/disable/expiry and must remain the single byte-retention authority for image, video, audio, and files. A future storage backend can change behind this service without changing ownership.

### Privacy defaults

- Persistent retention remains OFF until the OWNER explicitly enables a bounded policy.
- No global capture of every view-once message.
- Per-artifact and per-policy TTL/quota/size bounds are required.
- Deletion removes private bytes and preserves only the minimum audit/tombstone metadata required for accountability.
- Transport URLs/tokens/capabilities never enter durable logs, AI prompts, Memory, FAQ, or Knowledge Base.

## AI interaction with media

AI processing is a consumer of authorized artifacts, not an owner of media storage.

Potential bounded derived artifacts:

- image -> vision description/OCR-like semantic extraction when a configured provider supports it;
- audio/voice -> transcription when explicitly authorized;
- video -> bounded frame sampling plus optional audio transcription, with duration/size/token limits;
- file -> type-specific extraction only through registered tools.

Every derived artifact must record source artifact ID, model/provider, operation, timestamp, and retention state. Derived text is not automatically a Memory or Knowledge Base item. Promotion into Memory Engine or Knowledge Base must use their existing managed CRUD/visibility/source rules.

The knowledge hierarchy remains:

`Identity Registry -> Memory -> FAQ -> Knowledge Base -> Project Intelligence -> Internet -> AI reasoning`

No second AI router is introduced. Existing AI/reply-planner/tool-dispatch paths remain authoritative.

## Delivery and approval interaction

Media response generation does not weaken outbound authority. Ordinary external contacts remain approval-first unless an exact active OWNER contact automation policy permits the exact response category. OWNER media inspection commands return only to the exact OWNER control chat.

Content/media binding now covers the exact media locator, kind, and caption alongside the existing text hash, so a queued authorization cannot be reused for different media. Binding to a durable private artifact identity remains future work and arrives with the Private Media Artifact service.

## Safe implementation phases

1. **Done.** Rebase/port PR #38 onto P0 `main`, renumbering migrations and preserving the P0 worker/Command Center changes.
2. **Done.** Add explicit WAHA image/video/voice/file adapter methods and mock-only request-contract tests; do not change live routing yet.
3. **Done.** Add media-type-aware Outbound Queue dispatch after final P0 authorization, with fail-closed unknown/conflicting types and no automatic replay on uncertain sends. Producer-side media is canonicalized at one boundary before the queue row is created.
4. **Not started.** Restore/validate `.vv` image behavior on the new main and add truthful video/audio handling only when exact capability evidence is available. Classification exists; the command handler does not.
5. **Not started.** Introduce the single Private Media Artifact service and PostgreSQL metadata only after storage/retention policy tests are defined; default retention OFF.
6. **Not started.** Add bounded image/video/audio AI-derived-artifact processing through existing Tool Registry/AI boundaries. No automatic Memory/KB promotion.
7. **Partially done.** The active WAHA build was inspected for the webhook session contract (`populateSessionInfo`, `WAHAWebhook` DTO). View-once/revocation payload metadata has not been re-inspected against the deployed engine beyond the existing classification fixtures. If a required capability is absent, document the exact gap before considering an isolated Baileys prototype. Never run WAHA and Baileys simultaneously in production.

## Required validation before review-ready

- migration chain from 001 through the successor migrations;
- full pytest/coverage;
- OWNER permission and downgrade regressions;
- source-ID/marker/MIME conflict regressions;
- image/video/audio endpoint dispatch tests using mocks only;
- P0 final worker authorization still blocks unauthorized media rows;
- stale/expired capability cannot send;
- uncertain transport outcome cannot blindly replay;
- retention OFF stores no persistent media bytes;
- enabled retention uses exact artifact identity, TTL/quota/size limits, delete/disable semantics and privacy-bounded audit;
- AI-derived artifacts cannot silently become Memory/FAQ/Knowledge;
- revocation/view-once metadata correlation is exact-source and capability truthful.

## Live safety

No implementation or validation in this track reconnects the restricted real WhatsApp account or sends messages to real contacts. Tests use mocks, isolated local containers, or explicitly safe staging only. No claim is made that a historical WhatsApp restriction was caused by any specific Zina event, and no claim of deleted/view-once recovery is made for bytes the active transport never exposed.
