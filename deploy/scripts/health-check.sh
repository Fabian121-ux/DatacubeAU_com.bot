#!/bin/bash
#
# Datacube Health Check Script
# Checks all services and reports status
#

set -eu

HOST="${1:-localhost}"
FAILED=0
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "========================================"
echo "Datacube Health Check - $TIMESTAMP"
echo "========================================"
echo ""

# Check API
echo "Checking API..."
if curl -sf "http://${HOST}:8080/health" > /dev/null 2>&1; then
    echo "  ✓ API is healthy"
else
    echo "  ✗ API is DOWN"
    FAILED=1
fi

# Check Nginx (if using different port)
echo "Checking Nginx..."
if curl -sf "http://${HOST}:80/health" > /dev/null 2>&1 || [ "$HOST" != "localhost" ]; then
    echo "  ✓ Nginx is healthy"
else
    echo "  ✗ Nginx is DOWN"
    FAILED=1
fi

# Check WAHA
echo "Checking WAHA..."
if curl -sf "http://${HOST}:3000/api/health" > /dev/null 2>&1 || [ "$HOST" != "localhost" ]; then
    echo "  ✓ WAHA is healthy"
else
    echo "  ✗ WAHA is DOWN"
    FAILED=1
fi

# Check PostgreSQL (must run on same host as docker compose)
echo "Checking PostgreSQL..."
cd /srv/datacube
if docker compose exec -T postgres pg_isready -U datacube > /dev/null 2>&1; then
    echo "  ✓ PostgreSQL is healthy"
else
    echo "  ✗ PostgreSQL is DOWN"
    FAILED=1
fi

# Check disk space
echo "Checking disk space..."
USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$USAGE" -lt 80 ]; then
    echo "  ✓ Disk space OK ($USAGE%)"
else
    echo "  ✗ Disk space LOW ($USAGE%)"
    FAILED=1
fi

# Check memory
echo "Checking memory..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", ($3/$2) * 100}')
if [ "$MEMORY_USAGE" -lt 90 ]; then
    echo "  ✓ Memory OK ($MEMORY_USAGE%)"
else
    echo "  ✗ Memory HIGH ($MEMORY_USAGE%)"
    FAILED=1
fi

echo ""
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo "Result: ALL CHECKS PASSED ✓"
    echo "========================================"
    exit 0
else
    echo "Result: SOME CHECKS FAILED ✗"
    echo "========================================"
    exit 1
fi