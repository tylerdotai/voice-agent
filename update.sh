#!/bin/bash
# Voice Agent Update Script
# Pulls latest changes, updates dependencies, verifies benchmark

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/voice-agent}"
LOG_FILE="/tmp/voice-agent-update.log"
BACKUP_BEFORE_UPDATE=true

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; exit 1; }
step() { echo -e "${BLUE}[STEP]${NC} $1" | tee -a "$LOG_FILE"; }

# Detect if running in install dir
detect_location() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "git"
    elif [ -f "$INSTALL_DIR/install.sh" ]; then
        echo "installed"
    else
        echo "unknown"
    fi
}

# Backup configuration before update
backup_config() {
    if [ "$BACKUP_BEFORE_UPDATE" != "true" ]; then
        return
    fi

    step "Backing up configuration..."

    local backup_dir="$INSTALL_DIR/backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$backup_dir/config_${timestamp}.tar.gz"

    mkdir -p "$backup_dir"

    # Backup essential config files
    tar -czf "$backup_file" \
        -C "$INSTALL_DIR" \
        --exclude='.venv' \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        baseline_loop.py \
        langgraph_agent/ \
        benchmark.py \
        pii_handler.py \
        failover_test.py \
        prd.json \
        AGENTS.md \
        2>/dev/null || true

    log "Backup created: $backup_file"

    # Keep only last 5 backups
    cd "$backup_dir" && ls -t config_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
}

# Pull latest from git
git_pull() {
    local loc_type=$1

    if [ "$loc_type" != "git" ]; then
        warn "Not a git installation - skipping git pull"
        return
    fi

    step "Pulling latest changes..."

    cd "$INSTALL_DIR"

    # Fetch latest
    git fetch origin

    # Check if updates available
    local local_hash=$(git rev-parse HEAD)
    local remote_hash=$(git rev-parse origin/voice-agent-build)

    if [ "$local_hash" = "$remote_hash" ]; then
        log "Already on latest version ($local_hash)"
        return
    fi

    log "Updates available: $local_hash → $remote_hash"

    # Stash any local changes
    if ! git diff --quiet; then
        warn "Local changes detected - stashing"
        git stash push -m "Update stash $(date)"
    fi

    # Pull
    git pull origin voice-agent-build

    log "Updated to $(git rev-parse --short HEAD)"
}

# Update Python dependencies
update_python_deps() {
    step "Updating Python dependencies..."

    export VIRTUAL_ENV="$INSTALL_DIR/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"

    # Ensure venv exists
    if [ ! -f "$INSTALL_DIR/.venv/bin/python" ]; then
        error "Virtual environment not found. Run install.sh first."
    fi

    # Upgrade pip
    .venv/bin/pip install --upgrade pip -q

    # Update requirements
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        .venv/bin/pip install -r "$INSTALL_DIR/requirements.txt" -q
        log "Dependencies updated"
    else
        warn "requirements.txt not found - skipping"
    fi
}

# Update Ollama models
update_models() {
    step "Updating Ollama models..."

    # Ensure Ollama is running
    if ! pgrep -x "ollama" > /dev/null; then
        log "Starting Ollama..."
        ollama serve &
        sleep 3
    fi

    # Get current models
    local models=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | grep -v "^$")

    for model in $models; do
        log "Updating model: $model"
        ollama pull "$model" 2>&1 | tee -a "$LOG_FILE" || warn "Failed to update $model"
    done

    log "Model update complete"
}

# Run benchmark to verify
run_verification() {
    step "Running benchmark verification..."

    export VIRTUAL_ENV="$INSTALL_DIR/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"

    cd "$INSTALL_DIR"

    if [ ! -f "benchmark.py" ]; then
        warn "benchmark.py not found - skipping verification"
        return
    fi

    # Run benchmark
    log "Running benchmark (this may take a few minutes)..."
    .venv/bin/python benchmark.py 2>&1 | tee -a "$LOG_FILE"

    # Check result
    if grep -q "20/20 passed" || grep -q "19/20 passed" || grep -q "18/20 passed"; then
        log "Benchmark verification: PASSED"
    else
        warn "Benchmark verification may have had issues - check log"
    fi
}

# Restart service
restart_service() {
    step "Restarting voice agent service..."

    if systemctl --user list-unit-files | grep -q "voice-agent.service"; then
        systemctl --user restart voice-agent
        log "Service restarted"
    else
        warn "Systemd service not found - manual restart required"
    fi
}

# Print success
print_success() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Voice Agent Updated Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Update log: $LOG_FILE"
    echo ""
    echo "Next steps:"
    echo "  systemctl --user status voice-agent   # Check status"
    echo "  journalctl --user -u voice-agent -f   # View logs"
    echo "  python baseline_loop.py                # Test manually"
    echo ""
}

# Main update flow
main() {
    echo "Voice Agent Updater"
    echo "==================="
    echo ""

    # Detect installation type
    local loc_type=$(detect_location)
    log "Installation type: $loc_type"

    # Run update steps
    backup_config
    git_pull "$loc_type"
    update_python_deps
    update_models
    run_verification
    restart_service
    print_success
}

main "$@"