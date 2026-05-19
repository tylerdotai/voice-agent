#!/bin/bash
# Voice Agent One-Line Installer
# Usage: curl -fsSL https://install.voice-agent.local | bash
# Or:    bash <(curl -fsSL https://install.voice-agent.local/install.sh)

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/voice-agent}"
INSTALL_URL="${INSTALL_URL:-https://install.voice-agent.local}"
LOG_FILE="/tmp/voice-agent-install.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; exit 1; }

# Check script is run as root/sudo
check_permissions() {
    if [ "$(id -u)" -eq 0 ]; then
        USE_SUDO=""
    elif command -v sudo &>/dev/null; then
        USE_SUDO="sudo"
    else
        error "This script requires root privileges. Please run with sudo or as root."
    fi
}

# Detect hardware and recommend model
detect_hardware() {
    log "Detecting hardware..."

    local cpu_cores=$(nproc 2>/dev/null || echo "4")
    local ram_kb=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
    local ram_gb=$((ram_kb / 1024 / 1024))
    local disk_free_gb=$(df -BG / 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo "0")

    # Check GPU
    local gpu_type="cpu_only"
    local vram_mb=0

    if command -v nvidia-smi &>/dev/null; then
        if nvidia-smi &>/dev/null; then
            gpu_type="nvidia"
            vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 | awk '{print $1}' || echo "0")
        fi
    elif [ -f /sys/class/drm/card0/device ]; then
        # AMD GPU check
        if grep -q "Radeon" /sys/class/drm/card0/device/vendor 2>/dev/null; then
            gpu_type="amd"
            # Try to get VRAM from sysfs
            local vram_sys=$(cat /sys/class/drm/card0/device/mem_info_vram_total 2>/dev/null || echo "0")
            vram_mb=$((vram_sys / 1024 / 1024))
        fi
    fi

    # Model recommendation logic
    local recommended_model="qwen2.5:0.5b"
    if [ "$gpu_type" = "nvidia" ] && [ "$vram_mb" -ge 12000 ]; then
        recommended_model="qwen2.5:3b"
    elif [ "$gpu_type" = "amd" ] && [ "$vram_mb" -ge 8000 ]; then
        recommended_model="qwen2.5:3b"
    elif [ "$ram_gb" -ge 32 ]; then
        recommended_model="qwen2.5:1.5b"
    elif [ "$ram_gb" -ge 16 ]; then
        recommended_model="qwen2.5:1.5b"
    elif [ "$ram_gb" -ge 8 ]; then
        recommended_model="qwen2.5:0.5b"
    else
        recommended_model="smollm2:360m"  # Minimal RAM fallback
    fi

    # Output detected info
    echo "HARDWARE_DETECTED=true"
    echo "RAM_GB=$ram_gb"
    echo "GPU_TYPE=$gpu_type"
    echo "VRAM_MB=$vram_mb"
    echo "CPU_CORES=$cpu_cores"
    echo "DISK_FREE_GB=$disk_free_gb"
    echo "RECOMMENDED_MODEL=$recommended_model"

    # Export for later use
    export DETECTED_RAM_GB=$ram_gb
    export DETECTED_GPU_TYPE=$gpu_type
    export DETECTED_VRAM_MB=$vram_mb
    export DETECTED_MODEL=$recommended_model
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    local missing_deps=()

    # Check for curl
    if ! command -v curl &>/dev/null; then
        missing_deps+=("curl")
    fi

    # Check for python3
    if ! command -v python3 &>/dev/null; then
        missing_deps+=("python3")
    fi

    # Check internet connectivity
    if ! curl -sf https://ollama.ai &>/dev/null; then
        warn "Internet connectivity check failed. Some downloads may not work."
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log "Installing missing dependencies: ${missing_deps[*]}"
        install_system_deps
    fi

    # Check Ollama
    if command -v ollama &>/dev/null; then
        log "Ollama already installed"
    else
        log "Installing Ollama..."
        install_ollama
    fi
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."

    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        $USE_SUDO apt-get update -qq
        $USE_SUDO apt-get install -y -qq curl python3 python3-venv >/dev/null 2>&1 || true
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        $USE_SUDO dnf install -y -q curl python3 >/dev/null 2>&1 || true
    elif [ -f /etc/arch-release ]; then
        # Arch
        $USE_SUDO pacman -Sy --noconfirm curl python3 >/dev/null 2>&1 || true
    fi

    log "System dependencies installed"
}

# Install Ollama
install_ollama() {
    log "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | $USE_SUDO sh
    log "Ollama installed"
}

# Create installation directory
setup_directory() {
    log "Setting up installation directory..."

    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    log "Installation directory: $INSTALL_DIR"
}

# Create Python virtual environment
setup_python() {
    log "Setting up Python environment..."

    if [ ! -d "$INSTALL_DIR/.venv" ]; then
        python3 -m venv .venv
        log "Python venv created"
    fi

    # Activate venv for this script's duration
    export VIRTUAL_ENV="$INSTALL_DIR/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"

    log "Python environment ready"
}

# Create requirements.txt if not exists
create_requirements() {
    if [ ! -f "$INSTALL_DIR/requirements.txt" ]; then
        cat > "$INSTALL_DIR/requirements.txt" <<'EOF'
faster-whisper>=1.0.0
kokoro-onnx>=0.9.0
requests>=2.31.0
langgraph>=0.0.20
onnxruntime-rocm>=1.18.0
EOF
        log "requirements.txt created"
    fi
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."

    export VIRTUAL_ENV="$INSTALL_DIR/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"

    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r "$INSTALL_DIR/requirements.txt" -q

    log "Python dependencies installed"
}

# Pull recommended model
pull_model() {
    log "Pulling AI model: $DETECTED_MODEL..."

    # Start Ollama service if not running
    if ! pgrep -x "ollama" > /dev/null; then
        $USE_SUDO systemctl start ollama 2>/dev/null || ollama serve &
        sleep 2
    fi

    ollama pull "$DETECTED_MODEL"

    log "Model $DETECTED_MODEL ready"
}

# Create systemd service
create_service() {
    log "Creating systemd service..."

    local service_name="voice-agent"
    local service_file="/etc/systemd/system/$service_name.service"

    $USE_SUDO tee "$service_file" > /dev/null <<EOF
[Unit]
Description=Voice Agent - Local Voice AI
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=OLLAMA_HOST=127.0.0.1:11434
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/baseline_loop.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    $USE_SUDO systemctl daemon-reload
    $USE_SUDO systemctl enable "$service_name" 2>/dev/null || true

    log "Systemd service created: $service_name"
}

# Verify installation
verify_installation() {
    log "Verifying installation..."

    export VIRTUAL_ENV="$INSTALL_DIR/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"

    # Check Ollama is running
    if ! pgrep -x "ollama" > /dev/null; then
        ollama serve &
        sleep 3
    fi

    # Check model is available
    if ! ollama list | grep -q "$DETECTED_MODEL"; then
        warn "Model not listed in ollama, but should be pulled"
    fi

    log "Installation verified!"
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Voice Agent Installed Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo "Model installed: $DETECTED_MODEL"
    echo "RAM available: ${DETECTED_RAM_GB}GB"
    echo "GPU detected: $DETECTED_GPU_TYPE"
    echo ""
    echo "Commands:"
    echo "  cd $INSTALL_DIR"
    echo "  python baseline_loop.py          # Run voice agent"
    echo "  python benchmark.py --verbose    # Run tests"
    echo ""
    echo "Systemd service:"
    echo "  systemctl --user start voice-agent    # Start"
    echo "  systemctl --user status voice-agent  # Check status"
    echo "  journalctl --user -u voice-agent -f   # View logs"
    echo ""
}

# Main installation flow
main() {
    echo "Voice Agent Installer"
    echo "====================="
    echo ""

    check_permissions
    detect_hardware
    check_prerequisites
    setup_directory
    setup_python
    create_requirements
    install_python_deps
    pull_model
    create_service
    verify_installation
    print_success
}

main "$@"