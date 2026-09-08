# Zina Implementation Roadmap

Status: engineering execution plan for the "Zina Hourly Engineering" autonomous routine. This is **not** a runtime source of truth — it describes what to build and in what order, not what Zina answers with at runtime. Every claim here was verified against the actual codebase at the commit noted below; a later run must re-verify before trusting any status marked here, per this doc's own rule.

Last verified: 2026-09-08, against `main` @ `0034587a90bb8d5a79bda41e85091cfea33b969d` (post-merge of PR #44), by a full three-way codebase audit (three parallel Explore passes covering Identity/Memory/FAQ/Knowledge, Command Center/Dashboard/Router/Tools/Scheduled Actions, and Project Intelligence/Internet/Observability). Phase 17 added 2026-09-08 against `main` @ `5aadd725ed9da08a5eb84eb42b64f0f45f231c79` (post-merge of PR #47; PR #48 was open, not yet merged, at the time of this audit) — that phase's own architecture map (Outbound Queue/`OutboundAuthorizationService`/Contact Automation Policy/Scheduled Actions/`_queue_broadcast`/migration numbering) was independently re-verified via a dedicated Explore pass, not carried over from the prior audit.

Status legend: **DONE** (production-ready per acceptance criteria) / **PARTIAL** (real, wired-in work exists but acceptance criteria are incomplete) / **STUB** (scaffolding only, not load-bearing) / **MISSING** (does not exist).

---

## Phase 0 — Foundational Safety Work

**Status: DONE.**

- P0 outbound authority (owner + external payload binding, recipient/text/media-locator/kind/caption/MIME/filename all bound into the authorization digest): merged via PR #43 (`05be9d9`), post-merge CI green.
- View-once/private-media pipeline reconciled against P0 and merged via PR #41 (`0c312f2`), post-merge CI green (main @ `7846331`).
- `.vv`/`.vvopen` command handler: implemented, wired into `CommandControlService`, 92 passing tests. (A stale claim in `docs/VIEW_ONCE_MEDIA_PIPELINE.md` that this was unimplemented was corrected in PR #44.)
- PrivateMediaArtifact metadata foundation (layer 1 only — no byte storage): merged via PR #44 (`3912cd5`→`0034587`). A follow-up hardening PR #45 fixes two P2 findings from an automated Codex review (unbounded field lengths could crash `flush()`; `transport_provenance` needed a closed allowlist rather than arbitrary text) — see Phase 11.

**Dependencies:** none. **Active PR:** none (PR #45 is a Phase-11 hardening follow-up, tracked there). **Testing status:** full suite green, migration chain 001→032 verified clean, DB leakage 0.

**Next step:** none — re-verify each run that main is still green before starting new work; this phase does not get new features, only regressions if something breaks it.

---

## Phase 1 — Identity Registry

**Status: PARTIAL, stub-leaning.**

Files: `services/identity_registry_service.py` (239 lines), model `IdentityRegistryEntry` (`schema.py:450`), API in `api/admin.py:1520-1568`. Wired into the real reply path (`bot_config_service.identity_reply()` → `reply_planner.py`), so it's not dead code — but the surrounding CRUD is thin and the matching logic is essentially untested.

| Capability | Status | Evidence |
|---|---|---|
| Create | PARTIAL | Upsert-only (`upsert_identity_registry`); no dedicated create; `ensure_defaults_from_profile()` auto-seeds 8 hardcoded entries |
| Read | PARTIAL | Only returns `is_enabled=True` rows; no fetch-by-key, no disabled-entry visibility |
| Update | DONE | Same upsert endpoint |
| Delete | MISSING | No delete route or service method anywhere |
| Disable | DONE | `payload.enabled` toggle in upsert |
| Search | MISSING | No query/filter param |
| Provenance/source | MISSING | No column on the model at all |
| Timestamps | DONE | `created_at`/`updated_at` |
| Aliases | DONE | JSON `aliases` column, used in scoring |
| Entity type | MISSING | Only a free-text `category` string |
| Relationships | MISSING | `entities` is a flat JSON list, not a real relationship structure |
| Dashboard | STUB | Only a read-only count on the Identity Status panel; no management UI |
| Tests | MISSING | No `test_identity_registry_service.py`; existing tests stub out `identity_reply()` entirely, so the real `score_entry`/`_special_answer` logic is unexercised (matches the 16% coverage figure) |

**Acceptance criteria (from mission):** Create, Read, Update, Delete, Disable, Search, provenance/source, timestamps, aliases, entity type, relationships where appropriate; dashboard management; tests; conversation integration (already present).

**Dependencies:** none blocking. **Active PR:** none yet. **Blocked work:** none.

**Next implementation step:** Add `source`/`provenance` and a typed `entity_type` column (migration), a dedicated `create()` that rejects on duplicate `registry_key` instead of silently upserting, a `delete()` (tombstone, consistent with the codebase's soft-delete convention elsewhere), single-entry fetch-by-key, and a search/filter endpoint. Add a real test suite exercising `score_entry`/`_special_answer` directly, not through a stubbed mock. This is the highest-priority gap after Phase 0 per the mission's own phase ordering.

---

## Phase 2 — Memory Engine

**Status: PARTIAL, close to production-ready.**

Files: `services/memory_service.py` (1194 lines), `memory_compaction_policy.py`, models `UserMemory`/`UserMemoryTimeline`. Dashboard: memory tab in `admin.html`, fully wired.

| Capability | Status | Evidence |
|---|---|---|
| Create/Read/Update/Delete/Disable/Search/Export | DONE | Full CRUD + `is_enabled` toggle + `q`/`status` search + `/admin/memory/export` |
| Source/provenance | PARTIAL | Exists on `UserMemoryTimeline.source` only, not on the core `UserMemory` profile row |
| Confidence | PARTIAL | Exists on timeline only, not on the profile row |
| Visibility | MISSING | No `visibility` field anywhere |
| Entity/project association | PARTIAL | `UserMemory.projects` is free text, not a real FK (blocked on Phase 14 not existing yet) |
| Observability | DONE | `memory_used`/`memory_hits` surfaced in conversation-inspector analytics |

**Acceptance criteria:** Create, Read, Update, Delete, Disable, Search, Export, source/provenance, visibility, timestamps, confidence, entity/project association; visible in AI Control Center; conversation responses expose memory use (already true).

**Dependencies:** entity/project association is capped until Phase 14 (Project Intelligence) exists.

**Next implementation step:** Add `visibility` and promote `source`/`confidence` to the `UserMemory` profile row itself (currently timeline-only). This is a small, additive migration + service change.

---

## Phase 3 — FAQ Semantic Layer

**Status: PARTIAL.**

Files: `services/faq_service.py` (1001 lines), models `FAQEntry`/`FAQImportCandidate`. Genuinely wired into the router (`reply_planner.py:225`).

| Capability | Status | Evidence |
|---|---|---|
| Categories/intents/variations/keywords/entities | DONE | Real columns, populated by `infer_category`/`infer_intent`/etc. |
| Semantic retrieval | PARTIAL | Lexical normalization + Jaccard/`difflib` fuzzy scoring — **not embedding-based**, despite the "semantic" naming |
| Analytics/usage counts | DONE | `usage_count`/`success_count`/`failed_count`, exposed via `/admin/faq/analytics` |
| Confidence/relevance | DONE | Per-entry `confidence_threshold` |
| Create/Read/Update/Delete/Disable | PARTIAL | No per-entry CRUD route — only bulk document replace (`/admin/faq/save\|replace\|upload`) and import-candidate approve/reject; no route to toggle a single entry's `is_enabled` |

**Acceptance criteria:** categories, intents, variations, keywords, entities, semantic retrieval, analytics, usage counts, confidence/relevance, Create/Read/Update/Delete/Disable; influence identity/help/project responses and Router (already true for identity/help/router).

**Dependencies:** none blocking.

**Next implementation step:** Add per-entry CRUD routes (edit a single entry's answer/category/variations without a full document replace; a direct enable/disable toggle). True embedding-based semantic retrieval is a larger, separate investment — not blocking for TEST READY, but should be logged as a known limitation in the release checklist rather than silently left as "semantic" in name only.

---

## Phase 4 — Knowledge Base

**Status: PARTIAL, stub-leaning on lifecycle.**

Files: models `KnowledgeDocument`/`KnowledgeChunk`, `chunking_service.py`, `retrieval_service.py`, API `api/knowledge.py`.

| Capability | Status | Evidence |
|---|---|---|
| Upload | DONE | `/admin/knowledge/upload` + `/text`, though the dashboard UI only wires the `/text` path |
| Edit | MISSING | No update/replace endpoint for existing content |
| Delete | MISSING | No DELETE route anywhere |
| Disable | MISSING | Model field exists (`is_enabled`), shown as a read-only badge, but no route/button to toggle it |
| Reindex | DONE | `/admin/knowledge/reindex/{id}`, wired to a UI button |
| Replace | MISSING | Same gap as edit |
| Extraction status | MISSING | Conflated with indexing `status` |
| Indexing status | DONE | Set by `index_document()` |
| Provenance | PARTIAL | `source_type`/`metadata_json` exist but no dedicated author/URL provenance fields |
| Searchable content | DONE | Lexical/fuzzy token-overlap scoring (not embeddings) |
| Metadata | DONE | `metadata_json` on both document and chunk |

**Acceptance criteria:** upload, edit, delete, disable, reindex, replace, extraction status, indexing status, provenance, searchable content, metadata; never immutable.

**Dependencies:** none blocking.

**Next implementation step:** This is the biggest lifecycle gap in the four knowledge-hierarchy domains — once uploaded, a document can currently only be reindexed, never edited, replaced, disabled, or deleted. Add delete (with `KnowledgeChunk` cascade or tombstone, consistent with other domains), disable-toggle route, and a replace/edit path that re-triggers reindexing.

---

## Phase 5 — Command Center

**Status: PARTIAL — real architecture violation found.**

Files: `services/command_catalog_service.py`, `command_control_service.py`, model `CommandCatalogEntry`.

| Capability | Status | Evidence |
|---|---|---|
| Command name/description/permission/enabled/category/analytics/help | DONE | All real columns, actively used |
| Aliases | PARTIAL | Only one `trigger_syntax` per catalog row; real aliases (`.commands`/`.cmd`, `.vv`/`.vvopen`/`.vvretain`, etc.) live as hardcoded Python dicts in `CommandControlService`, disconnected from the catalog model |
| Handler | PARTIAL | `handler_target` is descriptive metadata only — actual dispatch is hand-written `if/elif` chains, not resolved dynamically from it |
| Categories | PARTIAL | User/Admin/Internet/Media/Memory Commands all exist; **"Experimental Commands" does not exist anywhere** |

**Architecture violation (real duplication, not hypothetical):** `ReplyRule` (table `reply_rules`, evaluated in `RulesEngine._resolve_reply_rule` before AI/FAQ) is a second, parallel command-like system. Worse: the Command Center's own `/create-command`, `/edit-command`, `/delete-command` owner commands write directly into `ReplyRule`, **not** `CommandCatalogEntry` (`owner_command_service.py:544`). This means user-created custom commands bypass Command Center governance entirely — no permission level, no usage analytics, no `/cmdon`/`/cmdoff` enable/disable. This is exactly the "commands hidden inside Reply Rules" pattern the mission explicitly forbids.

**Acceptance criteria:** command, aliases, description, permission level, enabled/disabled, handler, category, analytics, help text; distinct categories including Experimental; nothing hidden in Reply Rules.

**Dependencies:** none blocking, but this should be fixed before Phase 6 dashboard work builds more UI on top of the wrong model.

**Next implementation step:** Migrate `/create-command`/`/edit-command`/`/delete-command` to write into `CommandCatalogEntry` instead of `ReplyRule`, add an "Experimental Commands" category, and move hardcoded alias dicts into the catalog's own alias support (may need a new `aliases` JSON column, matching the Identity Registry pattern). This is a real correctness/architecture fix, not a nice-to-have.

---

## Phase 6 — AI Control Center

**Status: PARTIAL — no unified concept yet, several capable APIs stranded without UI.**

There is no single "AI Control Center." `admin.html` (2134 lines) is a genuine, tabbed dashboard covering the older/core subsystems well, but has not kept pace with newer services.

| Area | Status |
|---|---|
| Identity, Memory, FAQ, Knowledge, Commands, Outbound Queue, AI/Router diagnostics | DONE (real tabs) |
| Conversations | PARTIAL — only a read-only inspector tab; takeover/export/analysis APIs exist with no UI |
| Scheduled Actions | MISSING UI — full CRUD API exists (`scheduled_actions_admin.py`), zero dashboard tab; `action_queue.html` is a separate, unlinked static page |
| Rules/Policies | PARTIAL — `ReplyRule` tab only; owner outbound-approval and contact-automation policies have no dashboard surface at all (WhatsApp-command-only) |
| Media Artifacts | MISSING — `private_media_artifact_service.py` has no admin API or UI whatsoever |
| Mobile-friendly | PARTIAL — viewport meta present and an overflow self-check exists in JS, suggesting genuine (if unverified) responsive intent |

**Acceptance criteria:** every page explains what/why/depends-on/health; management pages for Identity, Memory, FAQ, Knowledge, Commands, Conversations, Scheduled Actions, Outbound Queue, Rules/Policies, Media Artifacts, AI/Router diagnostics; CRUD where appropriate; mobile-friendly.

**Dependencies:** benefits from Phase 5's fix (don't build a Rules/Policies tab that further entrenches `ReplyRule` duplication).

**Next implementation step:** Add dashboard tabs for the three capabilities that already have full backend APIs but zero UI: Scheduled Actions, Media Artifacts (once Phase 11's admin API exists), and Conversation Takeover/Export. This is UI-only work riding on existing, tested services — low risk, high observability payoff.

---

## Phase 7 — Conversation Observability

**Status: PARTIAL, close — a real single-message dashboard exists, but the accountability layer has gaps.**

`recent_router_decisions()` (`admin.py:254-390`, aka `GET /conversation-inspector`) already surfaces: contact/phone/whatsapp_id, inbound message + timestamp, intent, decision_type/reason/confidence, identity_used/memory_used/faq_used/knowledge_used, ai_tokens/model/latency, selected_source/route/rejected_routes, final_response, fallback_reason. This is real, not aspirational.

**Missing:**
- No `internet_used` boolean parallel to the other `*_used` flags (only a hit count).
- **Outbound authorization/approval result is captured too late to be audited** — `router.py._save_audit_log` flushes the `RouterDecision` row *before* `outbound_authority` (approval_id, response_category) is added to the same dict later in the function. The persisted, queryable trail predates the authority decision.
- Tools proposed vs. executed: no mechanism exists at all (no function-calling/tool-proposal code found anywhere); `ToolDispatcherService`'s own audit entries use a different `AuditLog.action` that this endpoint never joins on.
- `project_context` field exists in the response dict but is always empty — no upstream source populates it (blocked on Phase 14).

**Acceptance criteria:** every inspection view exposes contact, phone/chat id, inbound message, timestamp, intent, route, Identity/Memory/FAQ/Knowledge/Project-Intelligence/Internet used, AI reasoning source, tools proposed/executed, authority decision, outbound authorization, response source, failure/block reason.

**Dependencies:** tools-proposed/executed needs Phase 9's authority generalization first; project_context needs Phase 14.

**Next implementation step:** Fix the ordering bug so `outbound_authority` is captured in the same audit row as the rest of the decision (small, local fix in `router.py`), and add a real `internet_used` boolean. These are both bounded, high-value fixes independent of the larger Phase 9/14 work.

---

## Phase 8 — Router + Conversation Engine

**Status: PARTIAL, close to production.**

Architecture is a deterministic, explainable staged waterfall (Identity → Memory → FAQ → Knowledge → Cache → Internet → OpenRouter last-resort), not a giant if/else tree and not literally "AI-first" (AI is explicitly last-resort by design — the mission's "AI-first but explainable" framing doesn't match the code, though the explainability half is real). `RouterDecision` rows are genuinely persisted and surfaced (confirmed, not dead code). `ConversationTakeoverService` and `ConversationOpenLoopService` are real state machines, not stubs.

**Acceptance criteria:** AI-first but explainable; Router coordinates rather than owns; Conversation Engine maintains context/takeover; decisions persisted.

**Dependencies:** none blocking.

**Next implementation step:** No urgent gap. If "AI-first" is meant literally (AI reasons over retrieved context rather than being a last-resort fallback), that's a deliberate architecture change to weigh with the user, not a bug to silently fix — flag for a decision rather than implementing unilaterally.

---

## Phase 9 — Tool Registry + Authority Engine

**Status: PARTIAL — one dispatcher confirmed (good), but Authority Engine is WhatsApp-outbound-scoped only, and one real bypass found.**

`ToolDispatcherService.execute()` is confirmed to be the single dispatch chokepoint — no duplication. But:
- The "Authority Engine" role is split across `RouterOutboundAuthorityService` + `OutboundAuthorizationService`/`_delivery_authorized`, and is **scoped only to outbound WhatsApp message delivery**. There is no general-purpose deterministic approve/deny layer for arbitrary tool calls — `ToolDispatcherService`'s own check is a simple permission-rank comparison, no human-in-the-loop step.
- **Real bypass found:** the Tool Registry has a `web.search` entry (`handler_target: "internet.search"`), but `ToolDispatcherService` has no adapter for it — calling it raises `"tool has no executable adapter"`. In practice `reply_planner.py` instantiates `InternetService` directly and calls it, **completely bypassing the Tool Registry/Authority boundary** for internet access. This directly contradicts the mission's Phase 15 requirement ("safe tool authorization" for Internet).

**Acceptance criteria:** one dispatcher (confirmed); AI proposes, Authority Engine deterministically approves/denies; execution supports permission/ownership/target/capability/audit/idempotency/retry; AI never the authority.

**Dependencies:** Phase 15 (Internet) is blocked on this being fixed to make "safe tool authorization" true rather than aspirational.

**Next implementation step:** Either add a real `ToolDispatcherService` adapter for `web.search` that calls `InternetService` (closing the bypass), or explicitly decide Internet is intentionally routed outside Tool Registry and document why — don't leave it as an unexplained gap. The former is more consistent with the stated architecture.

---

## Phase 10 — WhatsApp Outbound Safety

**Status: DONE — production-grade.**

This is the mature P0 work (Phases 0/11 of the prior routine iteration). Final delivery fence (`background_workers._delivery_authorized`) is fail-closed by design; confirmed scheduled actions and router replies cross the *same* fence (`scheduled_action_service.release_due` creates a plain `OutboundMessage`, `_delivery_authorized` recognizes it via `_is_exact_scheduled_action_binding` — one authority path, not a parallel one). Content/media identity (locator, kind, MIME, filename, caption) all bound into the authorization digest per PR #43.

**Next implementation step:** none — regression-only. Any future producer of `outbound_queue` rows must be audited against this fence before shipping (see Phase 0's fail-closed-by-default policy).

---

## Phase 11 — Private Media / View-Once

**Status: PARTIAL.**

- `.vv`/`.vvopen`/`.vv info`/`.vv list`/`.vv delete` command family: DONE, tested.
- `PrivateMediaArtifact` PostgreSQL metadata layer: DONE (PR #44), currently being hardened for two Codex-review findings (PR #45 — bounded-field validation, closed `transport_provenance` allowlist).
- Private byte storage (layer 2): NOT STARTED. `storage_locator` stays `NULL` on every row.
- No admin API or dashboard surface for `PrivateMediaArtifact` at all (confirmed by Phase 6 audit).
- `.vvretain on`: correctly refused — must stay refused until byte storage/TTL/quota exist.

**Acceptance criteria:** OWNER-only view-once (done); one shared `PrivateMediaArtifact` for image/video/audio/voice/view-once (metadata layer done, byte storage not started); PostgreSQL metadata authority, private byte storage abstraction, artifact id, source message id, content hash, MIME, filename, type, size, provenance, owner authorization, TTL, quota, size limits, delete, disable, cleanup, restart safety, audit (metadata-side items done; storage-side items not started).

**Dependencies:** PR #45 must merge before further Phase 11 work builds on the service.

**Active PR:** #45 (hardening), open.

**Next implementation step:** After #45 merges — (a) add an admin API + dashboard tab for `PrivateMediaArtifact` (list/disable/delete by OWNER), which is pure UI/API work on an already-tested service; (b) design the private byte storage abstraction (layer 2) as a separate, larger PR — this needs quota/TTL/cleanup/restart-safety design before any code, per the mission's explicit gate ("only after storage/retention policy tests are defined").

---

## Phase 12 — AI Media Intelligence

**Status: MISSING entirely.** Confirmed by direct search: zero matches for vision/transcription/frame-extraction/multimodal/DerivedArtifact anywhere in `bot_core/app`.

**Dependencies:** blocked on Phase 11's private byte storage existing (nothing to analyze without stored bytes) — although image-only vision analysis on an ephemeral WAHA-provided URL, without persistent storage, may be feasible sooner if scoped carefully (analyze-then-discard, never store).

**Next implementation step:** Not started, and should not start before Phase 11's byte storage design is settled, since `DerivedArtifact` needs a source artifact to reference. Lowest priority of the currently-unstarted domains.

---

## Phase 13 — Scheduled Actions

**Status: PARTIAL, close to production.**

Create/Read/Disable/Schedule/Target/Owner/Authority-policy/Failures/Next-run/Audit: all DONE and confirmed routed through the same outbound authority fence as everything else (no second scheduler, no bypass). Gaps: Update is reschedule-only (no payload/target edit), Delete is soft-cancel only (row persists forever), execution history is a single mutable JSON blob rather than an append-only log. No dashboard UI tab despite a complete API (see Phase 6).

**Next implementation step:** Add a dashboard tab (low-risk, API already exists and is tested) and consider whether true delete/payload-edit are actually needed before TEST READY, or can be deferred — soft-cancel may be an acceptable permanent design given the audit-trail requirement.

---

## Phase 14 — Project Intelligence

**Status: MISSING entirely.** No `Project` table/model exists in any of the 32 migrations. "Datacube AU"/"ZinaX"/"Moxiz Gateway" exist only as static, hardcoded Identity Registry entries with no status/goals/tasks/files/activity tracking. `contact_intelligence_service.py` tracks WhatsApp contacts (people), not projects. `UserMemory.projects`/`.goals` are free-text columns on a *contact's* profile, not a project domain.

**Dependencies:** this is a from-scratch build — new model, migration, service, and cross-references to Identity/Knowledge/Memory. Several other phases (Memory's entity/project association, Conversation Observability's `project_context`) are capped on this not existing.

**Next implementation step:** Design a `projects` table (project identity, current goals/status, associated knowledge/memory references, task/decision log, activity timeline) as a new domain owned by a new `ProjectIntelligenceService`, analogous in shape to Identity Registry but with its own lifecycle. This is a larger vertical slice — plan it as its own PR, not a quick add-on.

---

## Phase 15 — Controlled Internet Capability

**Status: PARTIAL — functionally real, but not tool-authorized.**

`InternetService` (354 lines, genuinely non-trivial: multi-provider fallback, quota checks, TTL cache) has real provenance tracking, auditability (`InternetUsageEvent`), and result attribution. Explicit routing is enforced by pipeline ordering (Internet only reached after Identity/Memory/FAQ/Knowledge fail), not by an independent guard. **Gap shared with Phase 9:** it is called directly by `reply_planner.py`, bypassing the Tool Registry/Authority boundary entirely — the registered `web.search` tool has no dispatcher adapter.

**Dependencies:** blocked on Phase 9's fix (add the missing dispatcher adapter, or explicitly document why Internet is exempt).

**Next implementation step:** Tracked under Phase 9 — this phase's only real gap is that one.

---

## Phase 16 — Testing Readiness

**Status: NOT YET.** Tally against the mission's TEST READY checklist, as of this run:

| Requirement | Status |
|---|---|
| Clean fresh database migration (001→latest) | DONE (verified to 032) |
| Full pytest green | DONE (783 passed) |
| Coverage above gate | DONE (75.12% vs 57% gate) |
| DB leakage = 0 | DONE |
| No unresolved P0 regressions | DONE |
| No duplicate outbound paths | DONE (confirmed single fence) |
| No unsafe retries | DONE (fail-closed, quarantines uncertain delivery) |
| No second router/scheduler/dispatcher | DONE (confirmed single instances of each) |
| All key dashboard CRUD working | **NOT DONE** — Knowledge (no edit/delete/disable), Identity (no delete/search), FAQ (no per-entry CRUD), Scheduled Actions/Media Artifacts (no UI at all) |
| Commands discoverable | PARTIAL — `/help`/`/commands` work, but the `ReplyRule` duplication (Phase 5) means some owner-created commands aren't governed by Command Center |
| Conversation observability functional | PARTIAL — real but missing tool-proposal and correctly-timed authority-outcome fields (Phase 7) |
| Mock WAHA integration green | DONE (existing suite is mock-based throughout) |
| Exact CI on main green | DONE |
| Deployment/startup docs updated | NOT VERIFIED this run |

**Not TEST READY yet.** The blocking items are dashboard CRUD completeness (Phases 1/3/4/6/13) and the Command Center/`ReplyRule` duplication (Phase 5) — both are about Fabian being able to *manage* Zina safely before controlled testing, not about WhatsApp-facing safety (which is already solid per Phase 10).

**Next implementation step:** Work Phases 1, 5, then 3/4/6/13 dashboard gaps, in that order, before attempting `docs/ZINA_CONTROLLED_TEST_PLAN.md`. Phase 17 (below) is additive and explicitly must not delay this work — it was appended after Phase 16 rather than renumbered into the middle of the list precisely so it never reads as higher priority than TEST READY.

---

## Phase 17 — Intelligent Outbound Message Library

**Status: STARTED — data model + CRUD + template rendering foundation only. Zero wiring, zero selection engine, zero outbound authority.**

### Why this exists

Requirement added 2026-09-08 (owner instruction): Zina must avoid sending the same generic message to every eligible contact. Inspired by the *architectural concepts* of SaleSmartly's targeted-broadcast feature (targeted recipient grouping, tags/attributes, reusable templates with variables, multiple message variants, campaign analytics, send/result tracking) — explicitly **not** its anti-ban/anti-detection strategy. Zina must never randomize message content to disguise bulk messaging or evade WhatsApp enforcement; variant selection here exists for relevance and analytics, never for evasion.

Long-term goal: Zina chooses the best appropriate *approved* message for each *authorized* contact instead of blindly broadcasting identical content.

### Authority separation (non-negotiable, matches Phase 0/10's existing model)

This phase answers exactly one question — **WHAT COULD ZINA SAY?** — and must never answer any of the following, which remain owned exactly where they already are:

| Question | Owner (unchanged) |
|---|---|
| May this contact receive this category of message? | `contact_automation_policies` (raw table) / `OwnerContactAutomationPolicyService` |
| May this exact action execute now? | `OutboundAuthorizationService` / `RouterOutboundAuthorityService` |
| Deliver this exact authorized payload. | `background_workers.py::_delivery_authorized` (the P0 fence), `OutboundMessage`/`outbound_queue` |

A selected/rendered message variant **does not grant outbound authority**. The required per-recipient flow, once a producer exists, is: determine eligibility → verify consent/OWNER authorization/automation policy → choose eligible message set → select best eligible variant → substitute permitted variables → freeze the exact resulting payload → bind recipient + resulting text + media metadata to authority → enqueue **one** recipient-specific `outbound_queue` row → the existing P0 fence runs immediately before WAHA, unchanged → send only if authorization remains exactly valid. There must never be a path from this library directly to WAHA.

### No duplicate broadcast system

Audited before writing any code (2026-09-08): `owner_command_service.py::_queue_broadcast` (`.broadcast`-style owner commands) is **not** a working fan-out mechanism — it deliberately stamps every row `delivery_policy="unauthorized_broadcast"`, a value `_delivery_authorized` never accepts, so every row it creates is permanently blocked at the fence by design (see its own docstring and `docs/VIEW_ONCE_MEDIA_PIPELINE.md`). There is currently no working single owner-authorized fan-out entry point anywhere in the codebase. This phase must **not** resurrect or repurpose `_queue_broadcast`, and must **not** invent a second scheduling/queue table parallel to `OutboundMessage`/`ScheduledAction`. A future "release a message-library selection to N recipients" producer must mint durable per-recipient `outbound_approvals`/`contact_automation_policies` grants and queue through the existing `OutboundMessage` model with a `delivery_policy` the fence already recognizes (or a new value explicitly added to `_delivery_authorized`, reviewed with the same rigor as PR #43) — exactly the same primitive `ScheduledActionService.release_due` already uses, not a parallel one.

### What's implemented (this run)

Purely additive, zero behavior change, nothing wired into any producer or delivery path — same safety shape as `PrivateMediaArtifactService` (PR #44):

- **Migration 034** (`bot_core/migrations/034_outbound_message_library.sql`): three new tables.
  - `outbound_message_sets` — `set_key` (unique), `name`, `description`, `category`, `purpose`, `channel`, `primary_language`, `selection_strategy` (closed allowlist, currently only `deterministic_score`), `created_by` (provenance), `is_enabled`, timestamps, `disabled_at`/`deleted_at`.
  - `outbound_message_variants` — FK to its set, `label` (unique per active set), `template_body`, `required_variables`/`optional_variables` (JSON), optional media locator/kind/MIME/caption, `language`, `tags`, bounded `weight` (1–100, for future bounded A/B weighting among *equivalent eligible* variants), `status` (closed allowlist: `draft`/`approved` — only `approved` is meant to ever be selected once a selection engine exists), lifecycle fields.
  - `outbound_variant_usage` — analytics/audit trail only (contact, set, variant, `outbound_queue_id`, `selection_score`, `selection_reason`, `source_automation`, `send_result`). Never consulted by the delivery fence; cannot grant authority.
- **Models**: `OutboundMessageSet`, `OutboundMessageVariant`, `OutboundVariantUsage` in `schema.py`, registered in `tests/conftest.py`'s `CLEANUP_MODELS` (ordered child-before-parent: usage → variant → set → the existing `OutboundMessage`).
- **Service**: `bot_core/app/services/outbound_message_library_service.py`, `OutboundMessageLibraryService` — Create/Read/Update(via recreate)/Disable/Delete for both sets and variants, all fail-closed on invalid/oversized input (mirrors `PrivateMediaArtifactService`'s bounded-field pattern, including the two Codex-review findings from PR #45 — oversized fields never reach `flush()`, and `selection_strategy`/variant `status`/`send_result` are closed allowlists rather than arbitrary caller text). A variant's `required_variables` must equal, exactly, the set of `{{token}}` placeholders in its `template_body` (checked at creation, both directions — no undeclared token, no unused declaration) — enforced again at render time as defense in depth. `render()` substitutes only from a caller-supplied `variables` dict; a missing or empty required variable fails the render closed with the exact missing names, and **no value is ever invented**, per the mission's identity-hierarchy rule.
- **Tests**: `tests/unit/test_outbound_message_library_service.py` — creation validation (allowlists, bounds, duplicate `set_key`/`label`, required/optional overlap), the required-variables-equals-template-tokens invariant, render success, render fails closed on missing/empty/absent variables, render never substitutes an undeclared optional variable, `only_approved` listing filter, disable→delete monotonic lifecycle for both sets and variants (idempotent, tombstone-preserving, excluded from listings, still individually fetchable-as-None once deleted), a deleted label being reusable, and usage-record creation/`send_result` update including its own closed allowlist.

### What's explicitly NOT in this run (future steps, in order)

1. **Selection Engine** (`OutboundMessageSelectionService` or similar) — deterministic scoring across purpose/category/language/contact attributes/conversation history/prior variants used/recency/preferences/tone/semantic relevance/historical performance, with AI allowed to *rank* natural-language suitability but never to grant authority. Must produce an explainable `(variant, score, reason)` triple, observable in conversation/outbound inspection (Phase 7). Depends on Contact gaining structured attributes/tags — today `contacts` has only free-form `identity_json` (Phase 1/Contact gap noted implicitly here; consider whether tags belong on `Contact` or a new join table before building the scorer, since `identity_json` is not queryable/indexable the way tag-based eligibility filtering needs).
2. **Producer wiring** — the actual per-recipient flow described in "Authority separation" above: an OWNER-initiated outreach plan that evaluates recipients individually (never a single input fanning out into a direct transport loop), reusing `contact_automation_policies`/`OutboundAuthorizationService` exactly as `ScheduledActionService.release_due` does today. This is where every outbound-safety test in the acceptance list below actually becomes exercisable (unauthorized/opted-out/disabled/wrong-category/over-limit/duplicate/blocked/ambiguous contacts must all produce zero outbound; payload mutation after authorization must make zero WAHA calls; duplicate campaign execution and restart/reconciliation must not duplicate outbound; one recipient's failure must not authorize another's send) — this PR intentionally stops short of it because it is exactly the kind of P0-shaped change that needs the same standalone review rigor PR #43 got, not a rider on a data-model PR.
3. **AI Control Center section** — "Outbound Messaging" pages (Message Sets, Variants, Contact Automation Policies, Automations, Scheduled Actions, Outbound Queue, Analytics, Opt-outs/Blocks) showing enabled state, variant count, usage, reply/failure rate where measurable, blocked-by-authority count, last used, selection strategy, recent selections, and the exact reason a message was selected. Blocked on Phase 6 generally (no AI Control Center concept exists yet) and, for reply/failure-rate analytics, on Phase 7's observability gaps.
4. **Personalization variable sourcing** — a resolver that pulls `{{first_name}}`/`{{project}}`/`{{company}}`/`{{appointment_time}}`/etc. from Identity Registry (`get_by_key`/`resolve_references`), `Contact`, and conversation context, and refuses (or falls back to another eligible variant) when a required variable has no authoritative value — `render()` already fails closed on a missing value; only the *sourcing* of that value from real domains is unbuilt.

### Acceptance criteria (from the requirement — tracked, not all met yet)

Create/Read/Update/Delete/Disable for sets and variants (**done**); template variables (**done** — rendering); multiple approved variants per set (**done**); deterministic scoring engine (**not started**); AI ranking assist (**not started**); bounded A/B weighting for analytics among equivalent eligible variants (`weight` column exists, **not consumed yet**); campaign/usage analytics (**partially done** — `OutboundVariantUsage` records selection + send result, no dashboard); authority separation preserved end-to-end (**done by construction** — nothing wired in yet, so nothing to violate); no second broadcast system (**confirmed, audited above**); consent/opt-out first-class (**deferred to producer wiring**, step 2 above); full outbound-safety test matrix from the requirement (fail-closed unauthorized/opted-out/duplicate/mutation/restart cases) — **deferred to step 2**, since none of it is exercisable before a producer exists.

**Dependencies:** none blocking Phase 0/10 (P0 safety is untouched and already DONE). Step 1 (Selection Engine) benefits from Contact gaining structured tags (currently free-text `identity_json` only). Step 2 (producer wiring) must be reviewed with P0-equivalent rigor before merge, same bar as PR #43.

**Next implementation step:** Build the Selection Engine (step 1) as its own scoped PR against this foundation — deterministic scoring first, explainable `(variant, score, reason)` output, before any AI-ranking assist. Do not build producer wiring (step 2) until the Selection Engine exists and is tested, and do not let either delay Phases 1/5 (still the actual blockers for TEST READY per Phase 16).
