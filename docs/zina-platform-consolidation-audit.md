# Zina Platform Consolidation Audit

Date: 2026-06-17

This audit reflects the repository state after the P0 stabilization work and before the full platform consolidation is complete. It is intentionally conservative: systems are marked partial when they exist but still overlap with legacy paths.

## Architecture Snapshot

- Frontend: a single static administration console at `bot_core/app/static/admin.html`, served by FastAPI through `admin_ui.py`.
- Backend: FastAPI application under `bot_core/app`, with async SQLAlchemy models in `models/schema.py`.
- Database: PostgreSQL, managed by SQL migrations in `bot_core/migrations`.
- WhatsApp: WAHA webhook ingestion in `api/inbound.py`, outbound queue delivery in `workers/background_workers.py`, WAHA client in `services/waha_client.py`.
- AI provider: OpenRouter client in `services/openrouter_client.py`, called by `core/reply_planner.py`.
- Runtime response path: `InboundRouter.process_event` normalizes WAHA payloads, resolves contacts, executes owner/user commands, calls `ReplyPlanner`, records router decisions, queues outbound messages, and logs timeline/summary data.
- Admin APIs: most management endpoints live in `api/admin.py`; knowledge-specific upload/search endpoints live in `api/knowledge.py`.

## Feature Map

| Feature | Purpose | Current Owner | Authoritative Owner | Database/Storage | API/Service | Dependencies | Duplicate Systems | Migration Required | Status |
| ------- | ------- | ------------- | ------------------- | ---------------- | ----------- | ------------ | ----------------- | ------------------ | ------ |
| Core identity | Answer who Zina, Fabian, Datacube AU, ZinaX are | `BotConfigService`, `IdentityRegistryService`, FAQ, reply rules | Identity Registry | `identity_registry`, `bot_config`, legacy FAQ/rules | `IdentityRegistryService`, `BotConfigService.identity_reply` | FAQ reference resolver, planner identity branch | FAQ identity entries, reply-rule identity rows, bot config profile | Move identity branch fully to registry and disable legacy rules | Partial |
| Commands | User/owner command metadata and execution | `OwnerCommandService`, `ReplyPlanner`, `CommandCatalogService`, legacy reply rules | Command Center | `command_catalog`, legacy `reply_rules` | `CommandCatalogService`, `OwnerCommandService`, planner command paths | owner auth, internet service, memory service | command-like reply rules, code default catalog, migration seed | Add execution metadata, migrate/disable command-like rules | In progress |
| Reply Rules | Deterministic keyword replies | `RulesEngine`, admin reply-rule endpoints | Reply Rules | `reply_rules`, `user_triggers`, `forced_reply_targets` | `RulesEngine`, admin `/reply-rules` | group/dm config, intent classifier | commands and identity stored as rules | Disable non-rule responsibilities, add duplicate workflow | Partial |
| FAQ | Approved question/answer knowledge | `FAQService` | FAQ Manager | `faq_entries`, `faq_import_candidates`, `core_faq.md` | admin FAQ endpoints, startup sync | identity reference resolver, planner FAQ branch | core file sync and candidate import both publish FAQ | Add source version/history and live parser state | Partial |
| Knowledge Base | Uploaded/indexed documents and chunks | `RetrievalService`, knowledge API | Knowledge Base Manager | `knowledge_documents`, `knowledge_chunks`, `qa_cache` | `api/knowledge.py`, `RetrievalService` | chunking, cache, planner retrieval | owner `/remember` stores global admin notes as documents | Add disable/delete/replace/reindex cleanup guarantees | Partial |
| Memory | User-specific profile and timeline | `MemoryService` | Memory Manager | `user_memory`, `user_memory_timeline`, `conversation_summaries`, `conversation_timeline` | admin memory endpoints, planner memory branch | contacts, messages, summaries | owner memory commands also create knowledge docs | Add enabled/delete/export/scoping controls | Partial |
| Projects | Project-specific context | FAQ/knowledge/identity fragments | Project Registry or Project Knowledge | none dedicated | none dedicated | identity, knowledge | scattered records | Create project registry or scoped knowledge model | Missing |
| Training | Candidate review and publishing | FAQ candidates only | Training Center | `faq_import_candidates` only | FAQ import/approve/reject | FAQ service | no cross-domain candidate workflow | Add domain-classified candidates/history | Missing |
| Conversations | Runtime audit and traces | `RouterDecision`, `Message`, timeline tables | Conversation Inspector | `messages`, `router_decisions`, `conversation_timeline`, `conversation_summaries`, `audit_logs` | admin decisions/inspector endpoints | planner diagnostics, inbound router | multiple log tables with overlapping views | Add detail trace/export/redaction and consistent source schema | Partial |
| WAHA infrastructure | WhatsApp session and delivery | `WAHAClient`, inbound webhook, background worker | WAHA Integration | `outbound_queue`, `waha_outages`, messages | WAHA client, admin WAHA endpoints | WAHA API, settings | dashboard status and outage views are split | Add live session/QR/status data and stale detection | Partial |
| Retrieval and synthesis | Choose context and generate answer | `ReplyPlanner` | Central Intelligence Layer | router decisions, cache, service tables | `ReplyPlanner`, `OpenRouterClient` | identity, memory, FAQ, knowledge, internet | direct deterministic returns for many normal questions | Introduce modular provider ranking and conflict policy | Partial |
| Analytics | Explain routing and usage | Router decisions, FAQ analytics, AI/internet usage | Router Analytics | `router_decisions`, usage events, FAQ counters | admin analytics endpoints | planner diagnostics | source diagnostics shape varies by path | Standardize trace schema and route labels | Partial |

## Redundant Pages And Services

- Admin commands page existed, but command execution was still partly represented by reply rules.
- Identity page and FAQ identity answers overlap with `BotConfigService.identity_reply`.
- FAQ upload/save/sync and FAQ import candidates are separate source paths without source-version tracking.
- Conversation Inspector, router decisions, messages, timeline, and summaries expose overlapping conversation history.
- WAHA dashboard/outage/status controls are split across usage and outage views.

## Obsolete Or Risky Database Fields

- Command-like rows in `reply_rules` are legacy compatibility records and should stay disabled after migration.
- Protected identity-like rows in `reply_rules` and FAQ should not be runtime authority.
- `command_catalog` previously lacked runtime execution fields, making usage static or unavailable.
- Knowledge documents do not yet have complete source lifecycle fields such as stable file hash, chunk count, replace lineage, and error details in one consistent management view.
- Memory records need explicit enabled/deleted/audit fields before they can be fully managed as first-class data.

## Data Requiring Migration

| Legacy Source | Record Type | New Destination | Transformation | Conflict Rule | Validation | Cleanup |
| ------------- | ----------- | --------------- | -------------- | ------------- | ---------- | ------- |
| Command-like Reply Rules | slash/help/status/start command rows | Command Center | create or update command catalog entries; disable legacy rules | command catalog name wins | unique command name | keep disabled rows for audit until verified |
| Identity Reply Rules | who/what identity rows | Identity Registry | map entity/aliases/facts | protected registry wins | protected record cannot be overwritten silently | disable rule rows |
| Identity FAQ entries | core identity Q/A | Identity Registry references plus FAQ links | preserve FAQ as references only | registry wins | answer may reference identity but not redefine it | mark as FAQ, not authority |
| FAQ candidates | imported Q/A | FAQ entries | normalize, dedupe, approve | normalized question+intent unique | parse question and answer present | keep candidate audit |
| Admin note knowledge | `/remember` documents | Knowledge Base or Memory Manager by scope | classify global vs user memory | user-specific memory must not enter global knowledge | source and scope required | migrate user-scoped facts out of documents |
| Conversation logs | messages/decisions/timeline | Conversation Inspector trace | correlate by message and decision ids | source trace wins when present | no fabricated attribution | retain raw logs |

## Risky Dependencies

- Live WAHA payload shape varies by `@c.us`, `@lid`, alternate ids, and push/contact names.
- OpenRouter must stay server-side and optional; failures should degrade gracefully.
- Local test environment currently skips DB integration tests when PostgreSQL is unavailable.
- Admin UI is a static large HTML file, which makes mobile-first redesign and reusable components harder.
- Some startup sync paths write data from `core_faq.md`; this must remain idempotent.

## Proposed Final Architecture

1. Keep FastAPI as the backend boundary and consolidate runtime orchestration into a central intelligence pipeline.
2. Move each domain behind one service: Identity Registry, Command Catalog, Reply Rules, FAQ, Knowledge, Memory, Training, WAHA, Conversation Trace.
3. Route all runtime decisions through a shared context schema with source metadata, confidence, precedence, and trace ids.
4. Store command metadata and execution counters only in Command Center; command handlers remain server-side.
5. Keep reply rules for deterministic non-command responses only.
6. Make Identity Registry protected and higher precedence than FAQ, knowledge, memory, and model output.
7. Add source-versioned FAQ and knowledge ingestion with approval, dedupe, and reindex steps.
8. Expand the admin API into resource-oriented endpoints with consistent validation and authorization.
9. Replace static dashboard assumptions with real live status, empty states, and stale-data warnings.

## Safe Implementation Order

1. Command Center authority: add command execution metadata, implement missing command handlers, disable legacy command rules.
2. Identity authority: route identity questions through registry first, version protected records, disable identity reply rules.
3. Reply Rules cleanup: add duplicate/conflict audit and bulk actions; prohibit command/identity categories.
4. FAQ source pipeline: add source/version records, live parse preview, approval, sync status, source links.
5. Knowledge lifecycle: add delete/disable/replace/reindex cleanup and chunk inspection.
6. Memory lifecycle: add enabled/delete/export/scoping and duplicate detection.
7. Conversation trace schema: normalize route decisions and add detail/export.
8. WAHA dashboard: live status, QR/session details, stale detection, protected actions.
9. Training Center: domain-classified candidate approval across identity, FAQ, knowledge, memory, and projects.
10. Mobile admin redesign and reusable page explanations.

## Current Consolidation Slice

The current patch implements step 1 partially:

- Adds execution metadata to `command_catalog`.
- Records usage for owner/user commands, `/global`, `!ask`, and internet commands.
- Implements `/help`, `/start`, and `/status` as real user commands.
- Adds migration `012_command_center_authority.sql` to disable legacy command-like and identity-like reply-rule rows without deleting them.
- Updates Command Center UI to display syntax, handler target, usage count, and last used time.

Remaining command work: editable command CRUD, test command action, recent usage history, server-side create/update/delete endpoints, and full removal of legacy command responsibilities after production verification.
