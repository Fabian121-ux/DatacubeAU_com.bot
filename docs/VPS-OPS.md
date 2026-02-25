# VPS Ops Runbook (Datacube AU)

## PM2 services

- `datacube-api`: Express API + embedded WhatsApp client + outbound queue worker
- `datacube-admin`: Next.js admin console

## Deploy / update

```bash
cd /opt/datacube-bot
git pull
npm install
cd admin && npm install && npm run build && cd ..
pm2 reload ecosystem.config.js --update-env
pm2 save
```

If this is first deploy:

```bash
pm2 start ecosystem.config.js
pm2 save
```

## Start / stop

```bash
pm2 start ecosystem.config.js
pm2 stop ecosystem.config.js
pm2 status
```

## Health checks

```bash
curl -s http://127.0.0.1:3001/health
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:3001/bot/status
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:3001/admin/numbers
```

Expected `/bot/status.state`: `connected`, `waiting_qr`, `disconnected`, or `booting`.

## QR / auth recovery

1. Login to admin.
2. Open `/admin/numbers`.
3. Add/select the target number.
4. Press **Pair** (calls `POST /bot/pair/:numberId`).
5. Open `/admin/numbers/:id` and scan the QR.

API-only pairing flow:

```bash
curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"phone":"2349036553377","label":"Primary"}' \
  http://127.0.0.1:3001/admin/numbers

curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://127.0.0.1:3001/bot/pair/<numberId>

curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://127.0.0.1:3001/bot/status/<numberId>
```

If auth files are corrupted:

```bash
cp -r session session.backup.$(date +%F-%H%M%S)
rm -rf session/<numberId>/*
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:3001/bot/disconnect/<numberId>
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:3001/bot/pair/<numberId>
```

## Queue recovery

- Queue is persisted in SQLite `message_queue`.
- On restart, `sending` entries are returned to `queued`.
- Dead-letter entries are visible in `/admin/logs` and `/admin/trends`.

## Required env variables

- `ADMIN_TOKEN`
- `API_SECRET_KEY`
- `OPENROUTER_API_KEY`
- `ADMIN_LOGIN_USERNAME`
- `ADMIN_LOGIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `API_EMBED_WA_CLIENT=true`

Recommended:

- `OPENROUTER_TIMEOUT_MS`
- `OPENROUTER_RETRY_ONCE`
- `OPENROUTER_CIRCUIT_FAILURE_THRESHOLD`
- `OPENROUTER_CIRCUIT_COOLDOWN_MS`
- `OUTBOUND_QUEUE_MIN_DELAY_MS`
- `OUTBOUND_QUEUE_MAX_DELAY_MS`
- `OUTBOUND_QUEUE_MAX_ATTEMPTS`
- `OUTBOUND_QUEUE_SEND_TIMEOUT_MS`
- `WA_DEFAULT_COUNTRY_CODE` (required if admins will type local numbers like `090...`)
