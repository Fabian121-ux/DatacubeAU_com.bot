#!/bin/bash
#
# Datacube Deploy Script
# Quick deployment automation for production servers
#

set -eu

DOMAIN="${1:-}"
ENV_FILE=".env.production"

echo "========================================="
echo "Datacube Production Deploy"
echo "========================================="

# Check environment file
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found!"
    echo "Copy from .env.example or your managed production template and configure it"
    exit 1
fi

# Load environment
export $(cat "$ENV_FILE" | grep -v '^#' | xargs)

# Deleted-message lifecycle requires the combined event gateway and message.revoked.
# Refuse a stale production env instead of silently letting Compose override safe defaults.
EXPECTED_HOOK_URL="http://api:8080/webhooks/waha-events"
if [ "${WHATSAPP_HOOK_URL:-}" != "$EXPECTED_HOOK_URL" ]; then
    echo "Error: WHATSAPP_HOOK_URL must be $EXPECTED_HOOK_URL"
    echo "Current value: ${WHATSAPP_HOOK_URL:-<unset>}"
    exit 1
fi
case ",${WHATSAPP_HOOK_EVENTS:-}," in
    *,message.revoked,*) ;;
    *)
        echo "Error: WHATSAPP_HOOK_EVENTS must include message.revoked"
        echo "Recommended value: message,message.any,message.revoked"
        exit 1
        ;;
esac

echo "Building and starting services..."
docker compose build
docker compose up -d

echo "Waiting for services to be healthy..."
sleep 10

# Check health
echo "Running health checks..."
./deploy/scripts/health-check.sh

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Services:"
echo "  API:      http://localhost:8080"
echo "  WAHA:     http://localhost:3000"
echo "  Nginx:    http://localhost:80"
echo ""
echo "Status:    docker compose ps"
echo "Logs:      docker compose logs -f"
echo "Health:    ./deploy/scripts/health-check.sh"
