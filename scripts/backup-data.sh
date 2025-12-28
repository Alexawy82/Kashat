#!/bin/bash
# LedgerLoop Data Backup Script
# Usage: ./scripts/backup-data.sh

set -e

BACKUP_DIR="/opt/kashat/backups"
DATA_DIR="/opt/kashat/data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/kashat_backup_$TIMESTAMP.tar.gz"

echo "=== LedgerLoop Backup ==="
echo "Timestamp: $TIMESTAMP"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "ERROR: Data directory $DATA_DIR does not exist"
    exit 1
fi

# Create backup
echo "Creating backup..."
tar -czf "$BACKUP_FILE" -C "$(dirname $DATA_DIR)" "$(basename $DATA_DIR)"

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "ERROR: Backup failed"
    exit 1
fi

# Clean old backups (keep last 7)
echo "Cleaning old backups (keeping last 7)..."
ls -t "$BACKUP_DIR"/kashat_backup_*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm

# List current backups
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/kashat_backup_*.tar.gz 2>/dev/null || echo "  (none)"

echo ""
echo "=== Backup Complete ==="
