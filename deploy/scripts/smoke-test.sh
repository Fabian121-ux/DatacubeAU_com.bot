#!/bin/sh
set -eu

if [ -f .env.production ]; then
  set -a
  . ./.env.production
  set +a
fi

base_url="${PUBLIC_BASE_URL:-http://localhost}"

echo "Checking /health"
curl -fsS "${base_url}/health"
echo

if [ -n "${ADMIN_API_TOKEN:-}" ]; then
  echo "Checking /admin/config/debug"
  curl -fsS -H "X-Admin-Token: ${ADMIN_API_TOKEN}" "${base_url}/admin/config/debug"
  echo
fi

if [ -z "${LOCAL_TEST_DM_WHATSAPP_ID:-}" ]; then
  echo "LOCAL_TEST_DM_WHATSAPP_ID is required for the end-to-end smoke test." >&2
  exit 1
fi

payload=$(cat <<EOF
{"chatId":"${LOCAL_TEST_DM_WHATSAPP_ID}","from":"${LOCAL_TEST_DM_WHATSAPP_ID}","notifyName":"Smoke Test","type":"text","text":{"body":"hello"},"isGroup":false}
EOF
)

echo "Posting end-to-end DM webhook"
response=$(curl -fsS -X POST "${base_url}/webhooks/waha" \
  -H "Content-Type: application/json" \
  --data "$payload")
printf '%s\n' "$response"

echo "$response" | grep -q '"status":"ok"' || {
  echo "Webhook route did not return status=ok." >&2
  exit 1
}

echo "$response" | grep -q '"action":"replied"' || {
  echo "WAHA outbound reply did not complete. Check the WAHA session, hook URL, and LOCAL_TEST_DM_WHATSAPP_ID." >&2
  exit 1
}
echo

if [ -n "${ADMIN_API_TOKEN:-}" ]; then
  echo "Checking recent messages"
  curl -fsS -H "X-Admin-Token: ${ADMIN_API_TOKEN}" "${base_url}/admin/messages/recent"
  echo
fi
