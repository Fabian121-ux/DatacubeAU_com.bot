# Testing Architecture

This document defines the production test strategy for the Zina WhatsApp Assistant backend.

The goal is not 100% coverage. The goal is 80% minimum coverage over business logic, with priority on the service, routing, and planner layers where wrong behavior can create bad replies, data loss, duplicate sends, or broken escalation.

## Current Audit

The repository currently has no `tests/` directory. The codebase is organized around FastAPI routes, SQLAlchemy async models, service classes, planner/router orchestration, and background workers.

Highest-risk business logic identified from the repository:

1. `ReplyPlanner`
   - Selects the reply source order: rules, rate limit, FAQ, cache, knowledge, memory onboarding, AI, fallback.
   - Creates `PlannedReply` diagnostics.
   - Builds and stores conversation summaries.
   - Decides when to escalate instead of answering.

2. Router decision logic
   - Normalizes inbound WAHA events.
   - Creates contacts and message rows.
   - Extracts profile facts before planning.
   - Persists router decisions.
   - Queues outbound replies.
   - Caches reusable answers and updates summaries.

3. `RetrievalService`
   - Hybrid keyword/fuzzy/phrase scoring.
   - KB threshold behavior.
   - Cache lookup/upsert behavior.
   - Prompt context construction.

4. `MemoryService`
   - Onboarding state transitions.
   - Name parsing.
   - Profile extraction from user messages.
   - Profile merge behavior.
   - Timeline fact logging.
   - Memory context generation for AI prompts.

5. `FAQService`
   - Markdown Q/A parsing.
   - DB synchronization.
   - Fuzzy matching and threshold behavior.

6. `BotConfigService`
   - Default config fallback.
   - Dynamic identity/profile loading.
   - Zina introduction and escalation text.
   - Identity prompt construction.

7. Background workers
   - Outbound queue delivery status transitions.
   - Retry/backoff behavior.
   - WAHA outage detection and reconnect attempts.

8. Admin API service layer
   - Identity, FAQ, profile, memory timeline, and queue endpoints.
   - Should be API-tested without browser/UI tests.

HTML/admin UI tests are intentionally out of scope for this phase.

## Test Layout

Use this structure:

```text
tests/
  unit/
    test_message_normalizer.py
    test_rules_engine.py
    test_reply_planner.py
    test_retrieval_service.py
    test_memory_service.py
    test_faq_service.py
    test_bot_config_service.py
    test_background_workers.py
    test_utils.py
  integration/
    conftest.py
    test_postgres_repositories.py
    test_memory_persistence.py
    test_faq_persistence.py
    test_outbound_queue_workflow.py
    test_waha_worker_boundaries.py
    test_admin_service_layer.py
  api/
    conftest.py
    test_admin_identity_api.py
    test_admin_faq_api.py
    test_admin_profiles_api.py
    test_admin_memory_api.py
    test_admin_queue_api.py
```

## Unit Tests

Unit tests should not require PostgreSQL, WAHA, OpenRouter, or a running FastAPI server. Use fakes or mocks for `AsyncSession`, WAHA, and OpenRouter boundaries.

Required unit coverage:

- Message classification:
  - DM versus group.
  - Mention detection.
  - Text extraction from common WAHA payload shapes.
  - Empty or non-text handling.

- FAQ matching:
  - Parses `## Q:` and `A:` markdown pairs.
  - Ignores malformed entries.
  - Deduplicates normalized questions.
  - Honors threshold and returns best match.

- Memory extraction:
  - Extracts profession, interests, projects, goals, communication style, and relationship.
  - Avoids obvious false positives.
  - Merges facts without duplicating existing values.

- Memory retrieval/context:
  - Builds prompt context from all profile fields.
  - Handles empty memory.
  - Handles partially populated profiles.

- Profile updates:
  - Upserts profile fields.
  - Logs timeline facts where expected.
  - Does not overwrite fields with `None`.

- Routing decisions:
  - No reply for ignored messages.
  - Reply path creates queued outbound message.
  - AI call is associated with inbound message when used.

- Confidence scoring:
  - Retrieval exact phrase beats weak match.
  - FAQ source boost is applied.
  - Empty queries return zero confidence.
  - Diagnostics include keyword, fuzzy, phrase, source boost, and final score.

- Conversation summaries:
  - Creates first summary.
  - Appends subsequent summaries.
  - Trims long summaries to the configured cap.

- Identity generation:
  - Defaults to Zina/Fabian.
  - Uses DB config overrides.
  - Prompt explicitly states Zina is not Fabian.
  - Escalation text uses configured owner name.

- Utility functions:
  - `normalize_text`.
  - `looks_complex`.
  - `is_greeting`.
  - Hashing helpers.

## Integration Tests

Integration tests should use a real PostgreSQL service. They should not use real WAHA or OpenRouter.

Required integration coverage:

- PostgreSQL repositories:
  - Run migrations before tests.
  - Verify SQLAlchemy models can insert/select/update/delete key entities.

- Outbound queue workflow:
  - Insert pending outbound messages.
  - Mock `WAHAClient.send_text`.
  - Verify success transitions to `sent`.
  - Verify failure transitions to `retrying`, then `failed` after max retries.
  - Verify retry backoff timestamps are updated.

- WAHA client boundaries:
  - Mock HTTP responses with `respx` or equivalent.
  - Verify request path, headers, and payload shape for send/start/status.
  - Verify retryable failures raise `WahaClientError`.

- Memory persistence:
  - Upsert memory.
  - Extract and persist profile facts.
  - Write timeline rows.
  - Delete/critical-clear expected rows.

- FAQ persistence:
  - Sync markdown into `faq_entries`.
  - Query best match from persisted entries.
  - Save replacement markdown and verify old entries are removed.

- Admin API service layer:
  - Exercise endpoint handlers through ASGI without browser automation.
  - Use admin token.
  - Assert DB side effects.

## API Tests

API tests should use FastAPI ASGI clients and a test database. Do not use Selenium, Playwright, or browser automation for this phase.

Required API coverage:

- Admin endpoints:
  - `/admin/config`
  - `/admin/identity`
  - `/admin/identity/status`
  - `/admin/test-reply`

- Profile endpoints:
  - `GET /admin/profiles`
  - `PUT /admin/profiles/{contact_id}`
  - `DELETE /admin/profiles/{contact_id}`

- FAQ endpoints:
  - `GET /admin/faq`
  - `POST /admin/faq/save`
  - `POST /admin/faq/upload`

- Memory endpoints:
  - `GET /admin/memory`
  - `GET /admin/memory/{contact_id}`
  - `PUT /admin/memory/{contact_id}`
  - `DELETE /admin/memory/{contact_id}`
  - `GET /admin/memory/{contact_id}/timeline`

- Queue endpoints:
  - `GET /admin/queue`
  - `POST /admin/queue/{queue_id}/resend`
  - `DELETE /admin/queue/{queue_id}`

## Test Fixtures

Recommended fixtures:

- `db_engine`: async SQLAlchemy engine against test PostgreSQL.
- `db_session`: transaction-scoped async session.
- `migrated_db`: applies migrations once per test session.
- `admin_headers`: `{"x-admin-token": "test-admin-token"}`.
- `normalized_dm_message`: representative DM `NormalizedMessage`.
- `normalized_group_mention`: representative group message with mention.
- `fake_waha_client`: deterministic send/status/start behavior.
- `fake_openrouter_client`: deterministic generated replies.

Use transaction rollback between tests where possible. For worker tests, explicit cleanup is acceptable because queue state is the behavior under test.

## Refactoring Guidance

Do not change production behavior for tests.

Allowed testability refactors, if needed later:

- Inject `OpenRouterClient` and `WAHAClient` factories into services/workers.
- Extract pure functions for retry/backoff and status parsing.
- Move startup worker registration into a small function that can be invoked without starting FastAPI.
- Isolate file access for `core_faq.md` behind a path parameter.

Constraints:

- Keep defaults identical.
- Keep endpoint contracts identical.
- Keep database schema unchanged unless the feature itself requires a migration.
- Keep network calls mocked in tests.

## Coverage Policy

Minimum coverage:

- 80% total business logic coverage.

Priority modules:

- `bot_core/app/services`
- `bot_core/app/core`
- `bot_core/app/workers`
- `bot_core/app/api/admin.py`

Do not chase 100%. Exclusions are acceptable for:

- HTML/static UI.
- Simple enum/model declarations.
- Deployment scripts.
- Defensive exception branches that require external service failures, provided boundary behavior is covered with mocks.

The CI workflow enforces:

```bash
pytest tests \
  --cov=bot_core/app \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-fail-under=80
```

## How To Run Tests Locally

Install runtime and test dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install pytest pytest-asyncio pytest-cov respx
```

Set test environment:

```bash
export PYTHONPATH="$PWD/bot_core"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test"
export DATABASE_URL_SYNC="postgresql://postgres:postgres@localhost:5432/datacube_bot_test"
export ADMIN_API_TOKEN="test-admin-token"
export STARTUP_VALIDATE_DB=false
export AI_ENABLED=false
export WAHA_SERVICE_URL="http://127.0.0.1:3999"
```

Apply migrations to the test database:

```bash
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f bot_core/migrations/001_init.sql
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f bot_core/migrations/002_expand_v1.sql
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f bot_core/migrations/003_assistant_layer.sql
psql "$DATABASE_URL_SYNC" -v ON_ERROR_STOP=1 -f bot_core/migrations/004_nextgen_intelligence.sql
```

Run tests:

```bash
pytest tests --cov=bot_core/app --cov-report=term-missing --cov-report=xml --cov-fail-under=80
```

Run a narrower subset:

```bash
pytest tests/unit
pytest tests/integration
pytest tests/api
```

## How To Add Tests

1. Add pure logic tests under `tests/unit`.
2. Add database-backed behavior tests under `tests/integration`.
3. Add endpoint contract tests under `tests/api`.
4. Mock WAHA/OpenRouter boundaries.
5. Assert decisions, status transitions, and persisted side effects.
6. Avoid asserting implementation details that do not affect behavior.

## Remaining Untested Risks Until Tests Are Added

- Reply source precedence regressions in `ReplyPlanner`.
- Queue worker duplicate-send or retry transition bugs.
- WAHA outage monitor recording too many outage rows or missing failed reconnects.
- FAQ sync replacing entries incorrectly.
- Profile extraction false positives.
- Conversation summary truncation losing important context.
- Admin API auth and DB side effects.
- Identity prompt accidentally allowing Zina to speak as Fabian.
