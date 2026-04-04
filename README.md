# Datacube AU WhatsApp Bot Backend

Local-first V1 backend for a WhatsApp bot using WAHA Core, FastAPI, and PostgreSQL. The current build supports rules-based routing, debug/admin inspection, knowledge ingestion with text-search fallback, and optional OpenRouter fallback that is disabled by default.

## Backend Scope

- inbound WAHA webhook handling
- DM replies
- group mention-only replies
- cooldown enforcement
- router decision logging
- audit log inspection
- knowledge document ingestion
- retrieval-based replies
- optional AI fallback behind env flags

## Folder Structure

```text
Dockerfile
docker-compose.yml
requirements.txt
.env.production.example
deploy/
  nginx/
    default.conf
  scripts/
    backup-postgres.sh
    run-migrations.sh
    smoke-test.sh
bot_core/
  app/
    main.py
    config.py
    db.py
    api/
      admin.py
      health.py
      inbound.py
      knowledge.py
    core/
      message_normalizer.py
      reply_planner.py
      router.py
      rules_engine.py
    models/
      enums.py
      schema.py
    services/
      chunking_service.py
      logging_service.py
      openrouter_client.py
      retrieval_service.py
      waha_client.py
    utils/
      hashing.py
      text.py
      time.py
  migrations/
    001_init.sql
  seeds/
    001_local_seed.sql
  examples/
    dm_webhook.json
    group_mention_webhook.json
    sample-knowledge.md
  scripts/
    test-dm-webhook.ps1
    test-group-webhook.ps1
```

## Project Setup

1. Install dependencies:

```bash
uv sync
```

2. Copy `.env.example` to `.env` and adjust values.

3. Create PostgreSQL database:

```bash
createdb datacube_bot
```

4. Run the schema migrations:

```bash
psql "$DATABASE_URL" -f bot_core/migrations/001_init.sql
psql "$DATABASE_URL" -f bot_core/migrations/002_expand_v1.sql
```

5. Load local seed data:

```bash
psql "$DATABASE_URL" -f bot_core/seeds/001_local_seed.sql
```

## Environment Setup

Important env vars:

- `DATABASE_URL`
- `WAHA_SERVICE_URL`
- `WAHA_SESSION_NAME`
- `ADMIN_API_TOKEN`
- `ENABLE_AUTO_REPLY`
- `GROUP_DEFAULT_REPLY_MODE`
- `GROUP_DEFAULT_COOLDOWN_SECONDS`
- `DM_DEFAULT_COOLDOWN_SECONDS`
- `KB_MIN_SCORE`
- `AI_ENABLED`

Startup validation will fail fast if required config is invalid. If `AI_ENABLED=true`, OpenRouter credentials and model names must be present.

For Docker deployments, keep these two WAHA URLs distinct:

- `WAHA_SERVICE_URL` is how this FastAPI app reaches the WAHA container, usually `http://waha:3000`.
- `WAHA_BASE_URL` is WAHA's own advertised base URL for dashboard, swagger, webhooks, and generated file URLs, usually `http://localhost:3000` or your public domain.

## Running Locally

Start FastAPI from the `bot_core` directory:

```bash
cd bot_core
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Health check:

```bash
curl http://localhost:8080/health
```

If `STARTUP_VALIDATE_DB=true`, the app will fail on boot when PostgreSQL is unavailable.

## Production Deployment Baseline

Files added for VPS deployment:

- [Dockerfile](c:/Users/cruzan/Documents/DatacubeAU_com.bot/Dockerfile)
- [docker-compose.yml](c:/Users/cruzan/Documents/DatacubeAU_com.bot/docker-compose.yml)
- [.env.production.example](c:/Users/cruzan/Documents/DatacubeAU_com.bot/.env.production.example)
- [default.conf](c:/Users/cruzan/Documents/DatacubeAU_com.bot/deploy/nginx/default.conf)
- [run-migrations.sh](c:/Users/cruzan/Documents/DatacubeAU_com.bot/deploy/scripts/run-migrations.sh)
- [backup-postgres.sh](c:/Users/cruzan/Documents/DatacubeAU_com.bot/deploy/scripts/backup-postgres.sh)
- [smoke-test.sh](c:/Users/cruzan/Documents/DatacubeAU_com.bot/deploy/scripts/smoke-test.sh)

1. Copy `.env.production.example` to `.env.production`.
2. Set `WAHA_IMAGE` to the WAHA Core image/tag you actually run.
3. Reuse the current WAHA credentials from your existing WAHA host config for `WAHA_API_KEY`, `WAHA_DASHBOARD_PASSWORD`, and `WHATSAPP_SWAGGER_PASSWORD`.
4. Set strong values for `POSTGRES_PASSWORD` and `ADMIN_API_TOKEN`.
5. Keep the internal Docker URLs exactly as follows:

```text
WAHA_SERVICE_URL=http://waha:3000
WHATSAPP_HOOK_URL=http://api:8080/webhooks/waha
WHATSAPP_HOOK_EVENTS=message
```

6. Set the public host values for your server:

```text
WAHA_BASE_URL=http://YOUR_DROPLET_IP:3000
PUBLIC_BASE_URL=http://YOUR_DROPLET_IP
```

7. Set `LOCAL_TEST_DM_WHATSAPP_ID` to a real WhatsApp ID you can use for an end-to-end reply test.
8. Build the API image:

```bash
docker compose --env-file .env.production build api migrate
```

9. Start Postgres and the backend API first:

```bash
docker compose --env-file .env.production up -d postgres api
```

10. Apply migrations:

```bash
docker compose --env-file .env.production --profile ops run --rm migrate
```

11. Start WAHA and the reverse proxy:

```bash
docker compose --env-file .env.production up -d waha nginx
```

12. Run the end-to-end smoke check:

```bash
sh deploy/scripts/smoke-test.sh
```

13. Create a database backup when needed:

```bash
sh deploy/scripts/backup-postgres.sh
```

This baseline uses Nginx as an HTTP reverse proxy. Before public internet exposure, terminate TLS in front of Nginx or replace the proxy layer with one that manages certificates automatically.

With the default compose file, WAHA is also published on `http://localhost:3000` so the dashboard and swagger UI can match the WAHA env settings in `.env.production`.

## WAHA Webhook Setup

If WAHA runs in the same Compose stack as this backend, point WAHA inbound webhook to:

```text
http://api:8080/webhooks/waha
```

Restrict WAHA webhook events to:

```text
message
```

This backend normalizes inbound message payloads. Sending broader WAHA events such as `session.status` to the same route will create noisy non-message webhook traffic that the router does not need.

If WAHA is outside this Compose network, use the backend's public URL instead:

```text
http://YOUR_DROPLET_IP/webhooks/waha
```

## DigitalOcean Same-Server Plan

Edit these files on the server:

- `.env.production`
- `docker-compose.yml`
- `deploy/nginx/default.conf` only if you later move the backend off port `8080`

Exact env values to set in `.env.production`:

```text
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8080
POSTGRES_USER=datacube
POSTGRES_PASSWORD=<strong-db-password>
POSTGRES_DB=datacube_bot
DATABASE_URL=postgresql+asyncpg://datacube:<strong-db-password>@postgres:5432/datacube_bot
DATABASE_URL_SYNC=postgresql://datacube:<strong-db-password>@postgres:5432/datacube_bot
WAHA_SERVICE_URL=http://waha:3000
WAHA_API_KEY=<reuse-the-value-from-your-current-waha-.env>
WAHA_SESSION_NAME=default
WHATSAPP_HOOK_URL=http://api:8080/webhooks/waha
WHATSAPP_HOOK_EVENTS=message
WAHA_BASE_URL=http://YOUR_DROPLET_IP:3000
PUBLIC_BASE_URL=http://YOUR_DROPLET_IP
ADMIN_API_TOKEN=<strong-admin-token>
LOCAL_TEST_DM_WHATSAPP_ID=<your-test-number>@c.us
```

Exact commands to run on the DigitalOcean server:

```bash
cp .env.production.example .env.production
nano .env.production
docker compose --env-file .env.production build api migrate
docker compose --env-file .env.production up -d postgres api
docker compose --env-file .env.production --profile ops run --rm migrate
docker compose --env-file .env.production up -d waha nginx
docker compose --env-file .env.production ps
sh deploy/scripts/smoke-test.sh
```

Exact verification steps:

1. `docker compose --env-file .env.production ps` should show `postgres`, `api`, `waha`, and `nginx` as running.
2. `curl http://YOUR_DROPLET_IP/health` should return `"database":"ok"` and a WAHA status payload instead of a WAHA connection error.
3. `sh deploy/scripts/smoke-test.sh` should return a webhook result containing `"status":"ok"` and `"action":"replied"`.
4. `curl -H "X-Admin-Token: <strong-admin-token>" http://YOUR_DROPLET_IP/admin/messages/recent` should show one inbound and one outbound message for the smoke test chat.
5. `curl -H "X-Admin-Token: <strong-admin-token>" http://YOUR_DROPLET_IP/admin/router-decisions/recent` should show a recent decision with `reply_sent=true`.

## Local Test Flow

1. Run migration and seed SQL.
2. Start FastAPI on `http://localhost:8080`.
3. Start WAHA and confirm its session name matches `WAHA_SESSION_NAME`.
4. Send a DM payload:

```powershell
powershell -ExecutionPolicy Bypass -File bot_core/scripts/test-dm-webhook.ps1
```

5. Send a group mention payload:

```powershell
powershell -ExecutionPolicy Bypass -File bot_core/scripts/test-group-webhook.ps1
```

6. Inspect recent decisions:

```bash
curl -H "X-Admin-Token: local-admin-token" http://localhost:8080/admin/router-decisions/recent
```

7. Inspect recent messages:

```bash
curl -H "X-Admin-Token: local-admin-token" http://localhost:8080/admin/messages/recent
```

8. Inspect recent audit logs:

```bash
curl -H "X-Admin-Token: local-admin-token" http://localhost:8080/admin/logs/recent
```

9. Upload sample knowledge:

```bash
curl -X POST "http://localhost:8080/admin/knowledge/upload" \
  -H "X-Admin-Token: local-admin-token" \
  -F "source_type=product_docs" \
  -F "file=@bot_core/examples/sample-knowledge.md"
```

10. Send a DM with a question matching the knowledge text and inspect the resulting `kb_reply` decision.

## Sample Test Payloads

Files:

- [dm_webhook.json](c:/Users/cruzan/Documents/DatacubeAU_com.bot/bot_core/examples/dm_webhook.json)
- [group_mention_webhook.json](c:/Users/cruzan/Documents/DatacubeAU_com.bot/bot_core/examples/group_mention_webhook.json)

You can also post them directly:

```bash
curl -X POST http://localhost:8080/webhooks/waha \
  -H "Content-Type: application/json" \
  --data @bot_core/examples/dm_webhook.json
```

## Debug and Admin Endpoints

- `GET /admin/logs/recent`
- `GET /admin/router-decisions/recent`
- `GET /admin/messages/recent`
- `POST /admin/test-reply`
- `POST /admin/group-mode`
- `GET /admin/config/debug`
- `POST /admin/knowledge/upload`
- `POST /admin/knowledge/text`
- `POST /admin/knowledge/reindex/{document_id}`
- `GET /admin/knowledge/search`
- `GET /admin/knowledge/documents`

All admin endpoints accept `X-Admin-Token` when `ADMIN_API_TOKEN` is configured.

## Verifying Behavior

DM:
- send `hello`
- expect `static_reply`
- send the same DM twice quickly
- expect the second response to be blocked by cooldown

Group:
- send a group message without a mention
- expect `ignore`
- send a group message with `@datacube bot`
- expect a reply

Knowledge:
- ingest a document
- send a matching question
- expect `kb_reply`

## How To Enable AI Later

Set these env vars:

- `AI_ENABLED=true`
- `OPENROUTER_API_KEY=...`
- `OPENROUTER_MODEL_LIGHT=...`
- `OPENROUTER_MODEL_DEEP=...`

AI fallback only runs after static and knowledge paths fail or score too low.

## Known Assumptions

- Knowledge search currently uses text scoring fallback instead of embeddings.
- `router_decisions` are written before outbound delivery so delivery failures remain inspectable.
- WAHA connectivity is checked in `/health`, but the app does not require WAHA to be reachable to start.
- The included production reverse proxy is an HTTP baseline and still needs TLS termination before internet exposure.
