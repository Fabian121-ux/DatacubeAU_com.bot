#!/bin/bash
#
# Datacube Backup Script
# Creates PostgreSQL backup and manages retention
#

set -eu

BACKUP_DIR="/srv/datacube/deploy/backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/datacube_bot_${TIMESTAMP}.dump"

echo "Starting backup..."

mkdir -p "$BACKUP_DIR"

cd /srv/datacube

# Create backup
echo "Creating database backup..."
docker compose exec -T postgres pg_dump -U datacube -d datacube_bot -Fc > "$BACKUP_FILE"

# Verify backup
if [ -s "$BACKUP_FILE" ]; then
    echo "Backup created: $BACKUP_FILE"
    SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo "Backup size: $SIZE"
else
    echo "ERROR: Backup file is empty!"
    exit 1
fi

# Manage retention
echo "Managing backups (keeping last $RETENTION_DAYS days)..."
cd "$BACKUP_DIR"
BACKUP_COUNT=$(ls -1 datacube_bot_*.dump 2>/dev/null | wc -l)

if [ "$BACKUP_COUNT" -gt "$RETENTION_DAYS" ]; then
    ls -1t datacube_bot_*.dump | tail -n +$((RETENTION_DAYS + 1)) | xargs -r rm
    echo "Cleaned up old backups"
fi

# Update symlink to latest
cd "$BACKUP_DIR"
ln -sf "datacube_bot_${TIMESTAMP}.dump" latest.dump

echo "Backup completed successfully!"
echo "Latest backup: $BACKUP_DIR/latest.dump"