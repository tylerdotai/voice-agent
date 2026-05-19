#!/bin/bash
# Backup Voice Agent Configuration
# Creates a timestamped backup of all config, excludes large files

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/voice-agent}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/voice-agent-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="voice-agent_${TIMESTAMP}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME.tar.gz"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# What to backup (only files that exist)
CONFIG_FILES=(
    "baseline_loop.py"
    "langgraph_agent/"
    "supervisor.py"
    "agent_server.py"
    "mcp_servers/"
    "benchmark.py"
    "pii_handler.py"
    "failover_test.py"
    "prd.json"
    "AGENTS.md"
    "install.sh"
    "update.sh"
    "sip_bridge.py"
    "a2a_protocol.py"
    "supervisor.py"
)

# What to exclude (large/runtime files)
EXCLUDE_PATTERNS=(
    --exclude='.venv'
    --exclude='.git'
    --exclude='__pycache__'
    --exclude='*.pyc'
    --exclude='*.log'
    --exclude='logs/*.log'
    --exclude='logs/*.jsonl'
    --exclude='*.onnx'
    --exclude='*.bin'
    --exclude='node_modules/'
    --exclude='.venv/lib/'
)

log "Creating backup: $BACKUP_NAME"

# Create backup
cd "$INSTALL_DIR"

# Build tar command - backup entire directory minus exclusions
TAR_CMD="tar -czf '$BACKUP_PATH'"

# Add exclusion patterns
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    TAR_CMD="$TAR_CMD $pattern"
done

# Backup everything in current directory
TAR_CMD="$TAR_CMD ."

eval "$TAR_CMD"

# Get size
BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)

log "Backup created: $BACKUP_PATH ($BACKUP_SIZE)"
ln -sf "$BACKUP_PATH" "$BACKUP_DIR/voice-agent_latest.tar.gz"
log "Latest symlink updated: $BACKUP_DIR/voice-agent_latest.tar.gz"

# Print backup info
echo ""
echo "Backup complete!"
echo "  Location: $BACKUP_PATH"
echo "  Size: $BACKUP_SIZE"
echo ""
echo "To restore:"
echo "  cd $INSTALL_DIR"
echo "  bash $INSTALL_DIR/scripts/restore_config.sh $BACKUP_PATH"
echo ""

# Keep only last 10 backups
cd "$BACKUP_DIR"
ls -t voice-agent_*.tar.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
