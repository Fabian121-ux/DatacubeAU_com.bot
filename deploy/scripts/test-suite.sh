#!/bin/bash
#
# Datacube Test Script
# Comprehensive testing procedures for deployment verification
#

set -eu

cd /srv/datacube

echo "========================================="
echo "Datacube Test Suite"
echo "========================================="
echo ""

FAILED=0

# ========================================
# Test 1: Service Status
# ========================================
echo "[TEST 1] Checking service status..."
docker compose ps

# ========================================
# Test 2: API Health
# ========================================
echo ""
echo "[TEST 2] Testing API health endpoint..."
if curl -sf http://localhost:8080/health | grep -q "database"; then
    echo "✓ API health check passed"
else
    echo "✗ API health check failed"
    FAILED=1
fi

# ========================================
# Test 3: Database Connection
# ========================================
echo ""
echo "[TEST 3] Testing database connection..."
if docker compose exec -T postgres pg_isready -U datacube > /dev/null 2>&1; then
    echo "✓ Database is ready"
else
    echo "✗ Database is not ready"
    FAILED=1
fi

# ========================================
# Test 4: WAHA Connectivity
# ========================================
echo ""
echo "[TEST 4] Testing WAHA connectivity..."
if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✓ WAHA is accessible"
else
    echo "✗ WAHA is not accessible"
    FAILED=1
fi

# ========================================
# Test 5: API -> WAHA Service Call
# ========================================
echo ""
echo "[TEST 5] Testing API -> WAHA service call..."
WAHA_API_KEY=$(grep "^WAHA_API_KEY=" .env.production | cut -d'=' -f2)
if [ -n "$WAHA_API_KEY" ]; then
    RESPONSE=$(curl -s -H "X-Api-Key: $WAHA_API_KEY" http://localhost:3000/api/sessions/default)
    if echo "$RESPONSE" | grep -q "session"; then
        echo "✓ API can communicate with WAHA"
    else
        echo "✗ API cannot communicate with WAHA"
        FAILED=1
    fi
else
    echo "⚠ WAHA_API_KEY not set, skipping test"
fi

# ========================================
# Test 6: Webhook Endpoint
# ========================================
echo ""
echo "[TEST 6] Testing webhook endpoint..."
WEBHOOK_RESPONSE=$(curl -s -X POST http://localhost:8080/webhooks/waha \
    -H "Content-Type: application/json" \
    -d '{"event":"message","payload":{"id":"test_123"}}')
if echo "$WEBHOOK_RESPONSE" | grep -q "ok"; then
    echo "✓ Webhook endpoint is responding"
else
    echo "⚠ Webhook returned unexpected response: $WEBHOOK_RESPONSE"
fi

# ========================================
# Test 7: Nginx Proxy
# ========================================
echo ""
echo "[TEST 7] Testing Nginx proxy..."
if curl -sf http://localhost:80/health > /dev/null 2>&1; then
    echo "✓ Nginx proxy is working"
else
    echo "⚠ Nginx proxy not accessible (may not be running)"
fi

# ========================================
# Test 8: End-to-End WhatsApp Message
# ========================================
echo ""
echo "[TEST 8] Testing end-to-end WhatsApp..."
echo ""
echo "  Instructions:"
echo "  1. Open WhatsApp on your phone"
echo "  2. Send a message to your bot: ${BOT_WA_NUMBER:-<your bot number>}"
echo "  3. Check if reply is received"
echo ""
read -p "  Press Enter after testing..."

# Check logs for incoming message
if docker compose logs --tail=20 api | grep -qi "message"; then
    echo "✓ Message processed by backend"
else
    echo "⚠ No message found in logs"
fi

# ========================================
# Test 9: Disk & Memory
# ========================================
echo ""
echo "[TEST 9] Checking resources..."
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", ($3/$2) * 100}')

echo "  Disk:  $DISK_USAGE%"
echo "  Memory: $MEMORY_USAGE%"

if [ "$DISK_USAGE" -lt 80 ] && [ "$MEMORY_USAGE" -lt 90 ]; then
    echo "✓ Resources OK"
else
    echo "✗ Resources low"
    FAILED=1
fi

# ========================================
# Summary
# ========================================
echo ""
echo "========================================="
if [ $FAILED -eq 0 ]; then
    echo "TEST RESULT: ALL TESTS PASSED ✓"
else
    echo "TEST RESULT: SOME TESTS FAILED ✗"
fi
echo "========================================="

exit $FAILED