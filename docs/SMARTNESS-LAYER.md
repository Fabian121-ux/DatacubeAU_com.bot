# Smartness Layer

## Router flow

Inbound DM pipeline:

1. Deduplicate by `message_id` (`processed_messages`)
2. User upsert + opt-in state lookup
3. Deterministic classification
4. Route execution
5. Response generation
6. Outbound enqueue (`message_queue`)
7. Audit/event logging (`events`, `trends_daily`)

## Deterministic route categories

- `STATIC_COMMAND`
- `CUSTOM_COMMAND`
- `KB_MATCH`
- `CACHE_HIT`
- `AI_REQUIRED`
- `HUMAN_HANDOFF`

Only `AI_REQUIRED` calls OpenRouter.

## AI reliability model

- Request timeout (`OPENROUTER_TIMEOUT_MS`)
- Retry once on retryable upstream errors
- Fallback model (`OPENROUTER_FALLBACK_MODEL`)
- Circuit breaker:
  - threshold: `OPENROUTER_CIRCUIT_FAILURE_THRESHOLD`
  - cooldown: `OPENROUTER_CIRCUIT_COOLDOWN_MS`

## Queue reliability model

- SQLite-backed queue (`message_queue`)
- 2-4s dispatch spacing (`OUTBOUND_QUEUE_MIN_DELAY_MS` / `OUTBOUND_QUEUE_MAX_DELAY_MS`)
- send timeout (`OUTBOUND_QUEUE_SEND_TIMEOUT_MS`)
- retry with exponential backoff
- dead-letter after max attempts (`OUTBOUND_QUEUE_MAX_ATTEMPTS`)

## Knowledge base

- Documents: `kb_documents`
- Chunks: `kb_chunks`
- Retrieval: keyword overlap + fingerprint boost
- Ingestion is admin-only (no private chat auto-ingestion)

