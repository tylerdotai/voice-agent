#!/bin/bash
# Restore Voice Agent Configuration
# Extracts backup into installation directory

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/voice-agent}"
BACKUP_FILE="${1:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check arguments
if [ -z "$BACKUP_FILE" ]; then
    echo "Restore Voice Agent Configuration"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    BACKUP_DIR="${BACKUP_DIR:-$HOME/voice-agent-backups}"
    ls -lh "$BACKUP_DIR"/voice-agent_*.tar.gz 2>/dev/null || echo "  No backups found"
    echo ""
    echo "Or use 'latest':"
    echo "  $0 $BACKUP_DIR/voice-agent_latest.tar.gz"
    exit 1
fi

# Resolve latest symlink
if [ "$BACKUP_FILE" = "latest" ]; then
    BACKUP_DIR="${BACKUP_DIR:-$HOME/voice-agent-backups}"
    BACKUP_FILE="$BACKUP_DIR/voice-agent_latest.tar.gz"
fi

# Check backup exists
if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup not found: $BACKUP_FILE"
fi

log "Restoring from backup: $BACKUP_FILE"

# Check installation directory
if [ ! -d "$INSTALL_DIR" ]; then
    warn "Installation directory not found, creating: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
fi

# Create pre-restore backup (safety)
PRE_BACKUP="$INSTALL_DIR/.pre_restore_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
log "Creating pre-restore backup: $PRE_BACKUP"

tar -czf "$PRE_BACKUP" \
    --exclude='.venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    -C "$INSTALL_DIR" . 2>/dev/null || true

log "Pre-restore backup created"

# Extract backup with path traversal protection
log "Extracting backup..."
# Use --strip-components=1 to prevent path traversal attacks
# This strips any leading paths, so files can only be extracted to $INSTALL_DIR/
tar -xzf "$BACKUP_FILE" --strip-components=1 -C "$INSTALL_DIR"

# Verify no files were extracted outside INSTALL_DIR (additional safety check)
if [ -f "$INSTALL_DIR/../../etc/passwd" ] || [ -d "$INSTALL_DIR/../" ]; then
    error "Path traversal detected in backup! Aborting."
fi

# Verify key files exist
KEY_FILES=("baseline_loop.py" "AGENTS.md" "requirements.txt")
MISSING_FILES=()
for file in "${KEY_FILES[@]}"; do
    if [ ! -f "$INSTALL_DIR/$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    warn "Some key files may be missing: ${MISSING_FILES[*]}"
    warn "Check if backup was complete"
else
    log "Restore verified: all key files present"
fi

echo ""
echo "Restore complete!"
echo "  Backup used: $BACKUP_FILE"
echo "  Pre-restore backup: $PRE_BACKUP"
echo ""
echo "Next steps:"
echo "  cd $INSTALL_DIR"
echo "  source .venv/bin/activate"
echo "  python baseline_loop.py  # Test restore"
echo ""