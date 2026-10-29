# Zina Implementation Roadmap

## Live verification delta — 2026-10-29 15:37 WAT (partial; not release approval)

This replaces the 15:34 WAT snapshot. The detailed domain audit below is still based on September code and remains historical. Exact open-PR heads, recent Actions runs, workflow YAML, migration inventory, and GraphQL review-thread resolution state were re-queried. Thread totals and unresolved counts are distinct: the counts below use each thread's actual `is_resolved` state; a replied-to thread remains unresolved until GitHub marks it resolved. PR #59's prior exact-head run #40882297507 passed on `dcda2dbbea7d45745ce53df3cdc145d785cf80c7`; this update will create a new documentation head and requires its own automatic CI result.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; latest main Tests run [#34219252390](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08 with 797 tests and 75.98% coverage, applying migrations 001–033. This is stale for the October feature set. The branch endpoint reports `protected=false`; the repository rulesets endpoint is empty. The classic protection read returned 403 to the connected integration, so issue [#54](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/54) remains open.

- **Open PRs and latest observed exact-head Tests evidence:**
  - #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca` — [run #40158094566](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40158094566) success; 856 passed, 76.26% coverage; migrations 001–034.
  - #49 `bcd0033e024b177561b8afd41589afe1897ba4de` — [run #39920982545](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39920982545) success; 896 passed, 76.67%; migrations 001–033 plus 036–037, not a contiguous chain on this branch.
  - #50 `f78bc9bb7ec6ef448e755c355adfa79ae4273ae1` — [run #40368630895](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40368630895) success; 825 passed, 76.47%; migrations 001–033 plus 035.
  - #55 `2da7283a9a9d0e27a3c25b9a47a86570c3f8c8b2` — [run #40010785239](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40010785239) success; 814 passed, 76.01%; migrations 001–033, schema audit and DB-leakage audit passed on this exact head.
  - #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba` — [run #40169146406](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40169146406) success; 811 passed, 76.01%; migrations 001–033.
  - #59 (this documentation PR), current pre-update head `8bd0a4791934cb457e7b9304521db76319e836b9` — [run #40893386314](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40893386314) was in progress at the latest check; prior head `04e7919b16a8ca932e466eda6ada852c0b20604c` passed [run #40891909325](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40891909325), 797 passed, 76.01%; migrations 001–033. This refresh will require its own exact-head run.
  - #60 `1644e2a338b53c7ec709d91163187d9d0b4af940` — [run #40849618517](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40849618517) success; 903 passed, 76.43%; migrations 001–033 plus 038–040, omitting 034–037.
  - #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f` — [run #40300425938](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40300425938) success; 809 passed, 76.01%; migrations 001–033.
  - #62 `97f30242198cd78097983c74ff0062c96c016605` — [run #40857332668](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40857332668) success; 843 passed, 76.01%; migration-sequence preflight passed and migrations 001–033 applied.
  - #63 `c6c493d28c1e27a267867cfe8be7a5005f777a28` — [run #40461018945](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40461018945) success; 801 passed, 76.04%; migrations 001–033.

  These are branch-local results, not a single integrated release candidate. The tests workflow on `main` still applies only the migrations present on main.

- **Separate historical integration evidence:** validation branch `validation/zina-integrated-pr48-49-50-20261023`, head `8a2e6cc604f9d744d0f95a9126360b0a4364db9f`, [run #39940318940](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/39940318940) passed 956 tests at 77.24% and validated fresh migrations 001–037 plus an installed 033→037 upgrade, schema audit and leakage audit. This is not the current #55 head, does not include migrations 038–040, and does not prove a second-run no-op.

- **Migration order:** #48=034, #50=035, #49=036–037, #60=038–040. The original duplicate-number collision has been reconciled in the current feature branches; the combined 001–040 chain is still unverified. Do not treat separate branch runs as integration proof.

- **Unresolved review threads (current GraphQL `is_resolved` state; unresolved / total):** #48=0/15; #49=1/80; #50=2/10; #55=0/0; #57=1/1; #59=1/1; #60=3/3; #61=0/0; #62=5/5; #63=0/0. #48's 15 threads are resolved; #49 has one unresolved retired-key-registry thread; #50 has two unresolved architectural findings. Zero unresolved threads does not itself establish independent approval.

- **P0 and architecture blockers:** #60 remains draft/unmerged; unknown or expired consent and terminal STOP must deny at the final worker fence. Current head `18f03f250786bd7af2ff67f2a4f10b75ed8deaf9` narrows the broad opt-out regexes and adds topic-qualified negative regressions. Exact-head [Tests #40892840458](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40892840458) passed **911 tests, 1 warning, 76.41% coverage**. That workflow still applies migrations 001–033 plus 038–040, omitting 034–037; it is not integrated migration proof. Three inline threads remain unresolved and independent review of lock ordering, consent-event immutability, and contact-wide alias policy is still required. The source-grounded finding is documented at [review comment #6499327781](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60#issuecomment-6499327781); keep it unresolved until independent review passes. #50 still needs human decisions for all introduction paths honoring disabled/deleted identity and a legacy-provenance strategy that does not infer seed status from `updated_at = created_at`. #49 remains a library foundation only; do not integrate it into live producers. #48 private-media retention stays OFF.

- **Deployment guard:** #62's current source rejects target/session-overriding URL parameters including libpq `options`, rejects multi-host URI targets, compares normalized migration/audit endpoints, removes inherited `PGHOSTADDR`, `PGPORT`, `PGOPTIONS`, `PGSERVICE`, and `PGSERVICEFILE`, and pins each migration `psql` session to `public`. Its exact-head tests still cover only migrations 001–033. Five inline threads remain unresolved; #57 overlaps with #62 and must not be merged independently while the integrated candidate is under review.

- **Still required for release:** fresh contiguous migrations 001–040; installed 033→040 upgrade; a second migration-runner invocation proving a no-op; exact-candidate schema and DB-leakage audits; complete P0 adversarial matrix; independent review of blocking threads; updated controlled-test plan and explicit human sign-off. Keep `main` protected by independent review/CI (issue #54); do not self-merge or bypass review.

- **Safety:** this documentation update does not change application code or migrations. No production DB operation, real WAHA send, production WAHA reconnection, private-media retention activation, merge, or review-thread resolution occurred.

## Live verification delta — 2026-10-28 06:30 UTC (partial; not release approval)

This delta records the latest inspected state; the full domain audit below was written against September code and must not be treated as current without re-verification.

- **Main:** `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`, last commit 2026-09-08. Latest main Tests run [#405](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/34219252390) passed on 2026-09-08; no newer main-branch run was returned by the branch-filtered Actions query. This does not establish current main-green for the October feature set.
- **Current P0 candidate:** PR [#60](https://github.com/Fabian121-ux/DatacubeAU_com.bot/pull/60), exact head `dd944fdff88afe6de64a82b3dff40786f99f8f26`. Tests run [#622](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40643929083) completed successfully on 2026-10-28: **900 passed, 1 warning, 76.41% coverage** (57% gate). The workflow applied migrations 001–033 and 038–040 only; the missing predecessors 034–037 mean this is not a contiguous integrated migration test.
- **Open feature heads:** #48 `3acacbfe14eabd7e279dfc720b4a46ca71f4f7ca`; #49 `bcd0033e024b177561b8afd41589afe1897ba4de`; #50 `f78bc9bb7ec6ef448e755c355adfa79ae4273ae1`; #55 `2da7283a9a9d0e27a3c25b9a47a86570c3f8c8b2`; #57 `d831ce4e3dd7e56f38d8563dc63abc44f8c37bba`; #59 (this documentation PR; see its live PR page for the moving head); #60 `dd944fdff88afe6de64a82b3dff40786f99f8f26`; #61 `8a1c1dbf4185db44ff026c811ae9f0db6dc9b72f`; #62 `4ab17cc6beee2a658304eafaf438cf9d511bbb26`; #63 `c6c493d28c1e27a267867cfe8be7a5005f777a28`. All remain open.
- **Migration plan:** #48=034, #50=035, #49=036–037, #60=038–040. The old duplicate 034 in #49 is absent from its current tree. PR #61's contiguous-sequence gate passes on its own branch but is unmerged; PR #62's deployment preflight is also unmerged. The current #60 workflow does not validate the combined 001–040 chain.
- **P0 review:** #60 remains draft with 3 unresolved inline threads covering consent/mapping concurrency and the append-only consent-history database guard. The current exact-head suite is green, but independent review has not approved the current head. Do not infer approval from owner replies or prior-head tests. #50 still has two architectural decisions open: all introduction paths must honor unavailable identity records, and legacy seed provenance cannot safely be inferred from timestamps already mutated by old reads. #49 has one unresolved retired-key-registry thread; #62 has one unresolved deployment-guard thread.
- **Still unproven for a release candidate:** contiguous fresh migrations 001–040; installed 033→040 upgrade and safe second run; exact-candidate DB-leakage audit; full P0 adversarial matrix; independent review of blocking threads; controlled-test readiness.
- **Safety posture:** unknown/revoked contact consent and terminal STOP must deny external delivery at the final worker fence. Preserve one authoritative outbound dispatcher, exact payload binding, and no blind retry after uncertain WAHA outcome. No live WhatsApp action is part of engineering verification.

## Phase 0 — Foundational Safety Work

**Status: PARTIAL for release readiness — the core outbound fence is present, but a required contact-policy gate remains open.**

- P0 outbound authority (owner + external payload binding, recipient/text/media-locator/kind/caption/MIME/filename all bound into the authorization digest): merged via PR #43 (`05be9d9`), post-merge CI green.
- View-once/private-media pipeline reconciled against P0 and merged via PR #41 (`0c312f2`), post-merge CI green (main @ `7846331`).
- `.vv`/`.vvopen` command handler: implemented, wired into `CommandControlService`, 92 passing tests. (A stale claim in `docs/VIEW_ONCE_MEDIA_PIPELINE.md` that this was unimplemented was corrected in PR #44.)
- PrivateMediaArtifact metadata foundation (layer 1 only — no byte storage): merged via PR #44 (`3912cd5`→`0034587`). A follow-up hardening PR #45 fixes two P2 findings from an automated Codex review (unbounded field lengths could crash `flush()`; `transport_provenance` needed a closed allowlist rather than arbitrary text) — see Phase 11.

**Dependencies:** none. **Active PRs:** #60 (draft/unmerged P0 consent gate) and #61 (migration-sequence CI guard, open for independent review). **Testing status:** #60 exact head `06973c39a495108a22ba6d8ad446b1f734567f02`, run [40146341322](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40146341322), passed 819 tests at 75.96% coverage with one existing Starlette/httpx TestClient deprecation warning (57% gate). Its branch applies 001–033 plus 038 only. Integrated 001–038, installed 033→038 upgrade, P0 adversarial matrix, and current DB-leakage evidence remain unverified.

**Release blocker:** issue [#56](https://github.com/Fabian121-ux/DatacubeAU_com.bot/issues/56) remains open pending independent review and integrated validation of PR #60 at head `06973c39a495108a22ba6d8ad446b1f734567f02`. Exact-head run [40146341322](https://github.com/Fabian121-ux/DatacubeAU_com.bot/actions/runs/40146341322) passed 819 tests, 75.96% coverage, one existing Starlette/httpx TestClient deprecation warning. The current mapping fence denies stale recipient mappings; the new consent-event TRUNCATE finding remains unresolved. Combined migrations, P0 adversarial matrix, and DB-leakage validation remain outstanding. Unknown/revoked consent and terminal opt-out must fail closed; no OWNER override or re-consent command exists.

**Next step:** obtain independent review of #60's OWNER-attested evidence model and terminal opt-out policy and #61's sequence guard; run the exact combined migration chain and installed upgrade; rerun the P0 adversarial matrix and DB-leakage audit; only then decide whether #56 can be closed. Keep the existing single delivery fence; do not add a second sender or run live WhatsApp tests autonomously.

---

## Phase 1 — Identity Registry

**Status: PARTIAL — lifecycle API/service support and direct tests are present on main; dashboard management, dedicated create semantics, a real relationship model, and consistent introduction behavior remain incomplete.**

Files: `bot_core/app/services/identity_registry_service.py`, `bot_core/app/models/schema.py` (`IdentityRegistryEntry`), and `bot_core/app/api/admin.py`. Current main baseline: `5aadd725ed9da08a5eb84eb42b64f0f45f231c79`; migration 033 is integrated.

| Capability | Status | Evidence |
|---|---|---|
| Create | PARTIAL | `POST /admin/identity/registry` is an upsert; there is no separate create operation that rejects duplicate keys. |
| Read | PARTIAL | List supports `q` and `include_disabled`; single-key GET includes disabled entries but excludes tombstoned rows. |
| Update | DONE | Existing upsert endpoint updates an entry. |
| Delete | DONE | `DELETE /admin/identity/registry/{registry_key}` tombstones `deleted_at`, disables the row, and audits the operation. |
| Disable | DONE | Enabled state is managed through the upsert; disabled entries remain inspectable through search/single-key GET. |
| Search | DONE | Substring search across key, name, category, and description, with optional disabled entries. |
| Provenance/source | PARTIAL | The `source` column exists and newly seeded defaults use `system_default`; pre-migration rows can remain NULL until PR #50's backfill policy is resolved. |
| Timestamps | PARTIAL | `created_at`/`updated_at` exist, but current main's scored `answer()` path updates `updated_at` on reads. It is not a reliable edit-history or provenance signal. |
| Aliases | DONE | JSON aliases are used by identity scoring. |
| Entity type | PARTIAL | Typed `entity_type` exists; legacy-row backfill remains unmerged and must not rely on the timestamp heuristic. |
| Relationships | MISSING | `entities` remains a flat JSON list, not a relational entity model. |
| Dashboard | STUB | Only a read-only count is exposed; there is no registry management UI. |
| Tests | PARTIAL | 14 direct tests cover seeding/idempotency, special and scored answers, scoring, reference resolution, single fetch, search, and tombstone behavior. Dashboard and every introduction caller are not covered by this service suite. |

**Acceptance criteria:** dedicated create/read/update/delete/disable/search, trustworthy provenance, timestamps, aliases, entity type, relationships where appropriate, dashboard management, direct tests, and consistent conversation integration.

**Current blockers and next steps:**

1. **Fix introduction lifecycle at one authoritative boundary.** PR #50's unresolved finding is valid: `BotConfigService.introduction_reply()` still builds the configured introduction directly, while first-time greetings, `/start`, and identity-like reply rules can call it without consulting the registry. Route those paths through a shared tombstone/disable-aware decision; add regressions for each caller. A guard confined to `identity_reply()` is insufficient.
2. **Choose a safe legacy-provenance policy before merging migration 035.** The current `updated_at = created_at` heuristic cannot prove a row was never edited: historical scored reads already advanced `updated_at` before migration 033 existed. Recommended safe default: preserve ambiguous pre-existing NULL provenance as `legacy_unknown`; set `system_default` only for new defaults inserted by the current seeder. Backfill `entity_type` separately from provenance where the key mapping is trustworthy. Human approval is required before changing this migration's semantics.
3. After the P0 contact-consent gate in issue #56 and the two PR #50 decisions, implement dashboard CRUD and decide whether a dedicated create endpoint is needed. Do not repeat delete/search/single-fetch/provenance-column work already present on main.

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

**Status: DONE for merged payload binding and uncertain-send quarantine; release readiness remains PARTIAL while Phase 0 contact consent is unmerged.**

The merged fence remains the single authority path: scheduled actions and router replies converge on the same outbound worker, and recipient/text/media locator/kind/MIME/filename/caption remain bound into the authorization digest. The newer exact-contact consent/opt-out check is still on draft PR #60 and must not be treated as deployed. Final delivery fence (`background_workers._delivery_authorized`) is fail-closed by design; confirmed scheduled actions and router replies cross the *same* fence (`scheduled_action_service.release_due` creates a plain `OutboundMessage`, `_delivery_authorized` recognizes it via `_is_exact_scheduled_action_binding` — one authority path, not a parallel one). Content/media identity (locator, kind, MIME, filename, caption) all bound into the authorization digest per PR #43.

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

**Not TEST READY yet.** Dashboard CRUD completeness and the Command Center/`ReplyRule` duplication remain product blockers. In addition, the explicit contact-consent/opt-out gate is still unmerged on main; do not run controlled external-contact tests until PR #60 is independently reviewed and the combined migration/P0/leakage gates pass.

**Next implementation step:** Work Phases 1, 5, then 3/4/6/13 dashboard gaps, in that order, before attempting `docs/ZINA_CONTROLLED_TEST_PLAN.md`.
