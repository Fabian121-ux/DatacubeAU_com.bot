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
    echo "Copy from .env.production.example and configure"
    exit 1
fi

# Load environment
export $(cat "$ENV_FILE" | grep -v '^#' | xargs)

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