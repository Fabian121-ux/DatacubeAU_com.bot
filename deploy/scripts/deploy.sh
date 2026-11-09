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
    echo "Copy from .env.production.example and configure every required secret"
    exit 1
fi

# Read only the deployment values needed for preflight. Compose reads the same
# file with --env-file, and each container receives an explicit allowlist in
# docker-compose.yml; the complete host file is never mounted into a service.
get_env_value() {
    awk -v key="$1" 'index($0, key "=") == 1 { print substr($0, length(key) + 2); exit }' "$ENV_FILE" \
      | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}
WHATSAPP_HOOK_URL="$(get_env_value WHATSAPP_HOOK_URL)"
WHATSAPP_HOOK_EVENTS="$(get_env_value WHATSAPP_HOOK_EVENTS)"
DATABASE_URL="$(get_env_value DATABASE_URL)"
DATABASE_URL_SYNC="$(get_env_value DATABASE_URL_SYNC)"
DATABASE_URL_RUNTIME="$(get_env_value DATABASE_URL_RUNTIME)"
ZINA_RUNTIME_DB_PASSWORD="$(get_env_value ZINA_RUNTIME_DB_PASSWORD)"

if [ -z "$DATABASE_URL" ] || [ -z "$DATABASE_URL_SYNC" ] || [ -z "$DATABASE_URL_RUNTIME" ] || [ -z "$ZINA_RUNTIME_DB_PASSWORD" ]; then
    echo "Error: migration-owner URLs, DATABASE_URL_RUNTIME, and ZINA_RUNTIME_DB_PASSWORD are required."
    exit 1
fi

# Deleted-message lifecycle requires the combined event gateway and message.revoked.
EXPECTED_HOOK_URL="http://api:8080/webhooks/waha-events"
if [ "$WHATSAPP_HOOK_URL" != "$EXPECTED_HOOK_URL" ]; then
    echo "Error: WHATSAPP_HOOK_URL must be $EXPECTED_HOOK_URL"
    echo "Current value: ${WHATSAPP_HOOK_URL:-<unset>}"
    exit 1
fi
case ",$WHATSAPP_HOOK_EVENTS," in
    *,message.revoked,*) ;;
    *)
        echo "Error: WHATSAPP_HOOK_EVENTS must include message.revoked"
        echo "Recommended value: message,message.any,message.revoked"
        exit 1
        ;;
esac

compose() {
    docker compose --env-file "$ENV_FILE" "$@"
}

echo "Building and starting services..."
compose build
compose up -d

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
