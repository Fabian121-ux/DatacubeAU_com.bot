# Datacube AU WhatsApp Bot Platform

Production-oriented WhatsApp automation platform with:

- WhatsApp connectivity via Baileys
- Express backend API
- Next.js Admin Console (`admin/`)
- OpenRouter AI routing
- SQLite (`sql.js`) persistence

## Core capabilities

- Persistent admin navigation under `app/(admin)/layout.tsx`
- Multi-number WhatsApp runtime with isolated sessions per number
- Live auth lifecycle (`booting`, `waiting_qr`, `connected`, `disconnected`)
- Number-scoped pairing/disconnect endpoints
- Deterministic router pipeline with idempotent inbound handling
- Admin CRUD custom commands
- Admin CRUD number management (`bot_numbers`)
- Knowledge base ingestion + chunk retrieval (`kb_documents`, `kb_chunks`)
- Persistent outbound queue with retry/backoff/dead-letter (`message_queue`)
- OpenRouter timeout + retry + circuit breaker
- Auditable events and trends (`events`, `trends_daily`)

## Process model

PM2 runs:

- `datacube-api` (includes WhatsApp client + queue worker + API)
- `datacube-admin` (Next.js admin app)

`datacube-bot` can still be run manually for standalone testing (`npm run bot:start`), but production flow uses the API process as the WhatsApp host.

## Quick start

1. Install dependencies

```bash
npm install
cd admin && npm install && npm run build && cd ..
```

2. Configure environment

```bash
cp .env.example .env
```

Important for local-format phone inputs (for example `090...`):

- set `WA_DEFAULT_COUNTRY_CODE` in `.env` (for example `234`)
- then local numbers are normalized to E.164 digits automatically

3. Start backend API (with embedded WA client)

```bash
npm run start
```

4. Start admin console

```bash
cd admin
npm run dev
```

Open `http://localhost:3000/login`.

## Vercel Deploy (Frontend)

This repository is a monorepo-style layout:

- Frontend: `admin/` (Next.js 14 app router)
- Backend: root-level Node/Express code (deploy separately to VPS)

To avoid Vercel `404: NOT_FOUND`, the Vercel project must build from `admin/`.

Required Vercel Project Settings:

- Framework Preset: `Next.js`
- Root Directory: `admin`
- Install Command: `npm ci`
- Build Command: `npm run build`
- Output Directory: leave empty/default
- Node.js version: 18+ (20 recommended)

Short Redeploy Checklist:

1. In Vercel Project Settings, set `Root Directory` to `admin`.
2. Confirm `Framework Preset` is `Next.js`.
3. Save settings, then trigger a new deployment from branch `main`.
4. Use **Redeploy** with **Use existing Build Cache = OFF** once.
5. Open the latest deployment URL directly and verify:
   - `/`
   - `/login`
   - `/admin`
6. Assign/refresh the production domain to that latest successful deployment.

Required Vercel Environment Variables:

- `ADMIN_API_BASE_URL` = your backend public URL (example: `https://api.example.com` or `http://69.164.244.66:3001`)
- `ADMIN_API_TOKEN` = same value as backend `ADMIN_TOKEN`
- `ADMIN_LOGIN_USERNAME`
- `ADMIN_LOGIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `NEXTAUTH_SECRET` (same as `ADMIN_SESSION_SECRET`)
- `NEXTAUTH_URL` = your Vercel frontend URL

Why this fixes 404:

- Next.js routes (`/`, `/login`, `/admin`, deep links) are served only when Vercel runs from the `admin` app root.
- Deploying from repository root can produce platform-level 404s because root is not the Next app package.

## API endpoints

All protected routes require `Authorization: Bearer <ADMIN_TOKEN>`.

- `GET /health`
- `GET /bot/status`
- `GET /bot/qr` (png)
- `GET /bot/qr?format=json`
- `POST /bot/pair/:numberId`
- `GET /bot/status/:numberId`
- `GET /bot/qr/:numberId`
- `POST /bot/disconnect/:numberId`
- `POST /bot/pairing-code`
- `POST /bot/reconnect`
- `GET /admin/numbers`
- `POST /admin/numbers`
- `PUT /admin/numbers/:id`
- `DELETE /admin/numbers/:id`
- `GET /admin/config`
- `PUT /admin/config`
- `POST /admin/config/invalidate-context`
- `GET /admin/trends`
- `GET /admin/logs`
- `GET /admin/users`
- `GET /admin/commands`
- `POST /admin/commands`
- `PUT /admin/commands/:id`
- `DELETE /admin/commands/:id`
- `GET /admin/training/documents`
- `POST /admin/training/documents`
- `GET /admin/training/documents/:id/chunks`
- `DELETE /admin/training/documents/:id`

Legacy `/api/v1/*` routes are still available for compatibility.

## Admin routes

- `/admin`
- `/admin/settings`
- `/admin/commands`
- `/admin/numbers`
- `/admin/numbers/:id`
- `/admin/training`
- `/admin/logs`
- `/admin/users`
- `/admin/trends`

## PM2

```bash
pm2 start ecosystem.config.js
pm2 save
```

See `docs/VPS-OPS.md` for operations and recovery steps.

## Production deploy commands

```bash
npm install
cd admin && npm install && npm run build && cd ..
pm2 delete datacube-api datacube-admin || true
pm2 start ecosystem.config.js
pm2 save
pm2 status
```

Health check:

```bash
curl -s http://127.0.0.1:3001/health
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:3001/admin/numbers
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:3001/bot/status
```
