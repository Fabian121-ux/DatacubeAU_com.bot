#!/bin/bash
#
# Datacube Monitoring Script
# Monitors service health and sends alerts on failure
#

set -eu

WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
FAILED_SERVICES=()

cd /srv/datacube

echo "Running monitoring check..."

# Check containers
for service in api postgres waha nginx; do
    STATUS=$(docker compose ps --format json "$service" 2>/dev/null | jq -r '.[0].State' 2>/dev/null || echo "unknown")
    if [ "$STATUS" != "running" ]; then
        FAILED_SERVICES+=("$service ($STATUS)")
    fi
done

# Check API health
if ! curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    FAILED_SERVICES+=("api:health")
fi

# Check database
if ! docker compose exec -T postgres pg_isready -U datacube > /dev/null 2>&1; then
    FAILED_SERVICES+=("postgres:ready")
fi

# Check disk space (warn if > 80%)
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    FAILED_SERVICES+=("disk:$DISK_USAGE%")
fi

# Check memory (warn if > 90%)
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", ($3/$2) * 100}')
if [ "$MEMORY_USAGE" -gt 90 ]; then
    FAILED_SERVICES+=("memory:$MEMORY_USAGE%")
fi

# Send alert if failures detected
if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    ALERT_MSG="[ALERT] Datacube Service Issues: ${FAILED_SERVICES[*]}"
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$TIMESTAMP] $ALERT_MSG"
    
    # Send to Discord webhook if configured
    if [ -n "$WEBHOOK_URL" ]; then
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"content\": \"$ALERT_MSG\"}"
    fi
    
    # Send email if configured
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$ALERT_MSG" | mail -s "[ALERT] Datacube Service Issues" "$ALERT_EMAIL"
    fi
    
    exit 1
fi

echo "All services healthy ✓"
exit 0