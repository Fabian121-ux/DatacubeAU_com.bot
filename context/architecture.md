# Datacube AU Bot Architecture

Core flow:
1. WhatsApp DM received by Baileys.
2. Message Router classifies: STATIC_COMMAND | FAQ_MATCH | CACHED_ANSWER | AI_REQUIRED | HUMAN_HANDOFF.
3. FAQ/cache responses return immediately when matched.
4. AI_REQUIRED messages call OpenRouter with context from /context files.
5. Responses are queued with outbound delay and logged with privacy-safe metadata.

Components:
- bot/: WhatsApp connection and session persistence
- router/: command + smartness routing
- ai/: prompt, OpenRouter client, FAQ matching
- db/: SQLite access for users, config, logs, cache, trends
- api/: secure admin and bot endpoints
- admin/: Next.js admin panel
