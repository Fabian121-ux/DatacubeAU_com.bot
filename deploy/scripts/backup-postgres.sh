#!/bin/sh
#
# PostgreSQL Backup Script
# Creates a database backup in custom format for pg_restore
#

set -eu

BACKUP_DIR="deploy/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/datacube_bot_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

echo "Creating database backup..."
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-datacube}" -d "${POSTGRES_DB:-datacube_bot}" -Fc > "$BACKUP_FILE"

echo "Backup written to $BACKUP_FILE"
ls -lh "$BACKUP_FILE"