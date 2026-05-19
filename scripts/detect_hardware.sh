#!/bin/bash
# Hardware Detection Script for Voice Agent
# Detects system specs and outputs JSON for model selection

set -euo pipefail

OUTPUT_FORMAT="json"  # default, can be "text" for debugging

# Detect CPU
detect_cpu() {
    local cpu_model=$(lscpu | grep "Model name:" | sed 's/Model name:\s*//' | xargs)
    local cpu_cores=$(nproc)
    echo "$cpu_model|$cpu_cores"
}

# Detect RAM
detect_ram() {
    local total_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local total_gb=$((total_kb / 1024 / 1024))
    echo "$total_gb"
}

# Detect GPU
detect_gpu() {
    local gpu_info=""
    local gpu VRAM

    # AMD GPU (ROCm)
    if command -v rocm-smi &>/dev/null; then
        gpu=$(rocm-smi --showproductname 2>/dev/null | grep -E " Radeon " | head -1 | xargs || echo "")
        if [ -n "$gpu" ]; then
            VRAM=$(rocm-smi --showmeminfo vram 2>/dev/null | grep "Total Memory" | awk '{print $4}' || echo "unknown")
            echo "amd|$gpu|$VRAM"
            return
        fi
    fi

    # NVIDIA GPU
    if command -v nvidia-smi &>/dev/null; then
        gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "")
        if [ -n "$gpu" ]; then
            VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 | awk '{print $1}' || echo "unknown")
            echo "nvidia|$gpu|$VRAM"
            return
        fi
    fi

    # Intel GPU (Linux)
    if [ -d /sys/class/drm ]; then
        local intel_gpu=$(ls /sys/class/drm/card*/device 2>/dev/null | head -1)
        if [ -n "$intel_gpu" ]; then
            # Check for Intel GPU via lspci
            if lspci 2>/dev/null | grep -iE "(vga|3d|display).*intel" | grep -qE "Arc|Radeon"; then
                echo "intel|integrated|unknown"
                return
            fi
        fi
    fi

    echo "cpu_only|none|0"
}

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID|$VERSION_ID"
    else
        echo "unknown|0"
    fi
}

# Detect available disk space
detect_disk() {
    local root_free_gb=$(df -BG / | tail -1 | awk '{print $4}' | tr -d 'G')
    echo "$root_free_gb"
}

# Check for required tools
check_dependencies() {
    local deps=("curl" "python3" "ollama")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo "MISSING_DEPS:${missing[*]}"
        return 1
    fi
    echo "OK"
}

# Calculate recommended model based on hardware
calculate_model() {
    local ram_gb=$1
    local gpu_type=$2
    local vram_mb=$3
    local cpu_cores=$4

    # Model recommendations based on hardware
    if [ "$gpu_type" = "nvidia" ] && [ "$vram_mb" -ge 16000 ]; then
        echo "qwen2.5:3b"  # RTX 4090 class - can handle larger models
    elif [ "$gpu_type" = "amd" ] && [ "$vram_mb" -ge 8000 ]; then
        echo "qwen2.5:3b"  # AMD 7900xtx class
    elif [ "$ram_gb" -ge 16 ]; then
        echo "qwen2.5:1.5b"  # 16GB+ RAM without discrete GPU
    elif [ "$ram_gb" -ge 8 ]; then
        echo "qwen2.5:0.5b"  # 8GB RAM - minimal model
    elif [ "$ram_gb" -ge 4 ]; then
        echo "smollm2:1.7b"  # Very low RAM - embedded model
    else
        echo "qwen2.5:0.5b"  # Minimal
    fi
}

# Main detection
main() {
    local cpu_info=$(detect_cpu)
    local cpu_model=$(echo "$cpu_info" | cut -d'|' -f1)
    local cpu_cores=$(echo "$cpu_info" | cut -d'|' -f2)
    local ram_gb=$(detect_ram)
    local gpu_info=$(detect_gpu)
    local gpu_type=$(echo "$gpu_info" | cut -d'|' -f1)
    local gpu_model=$(echo "$gpu_info" | cut -d'|' -f2)
    local vram_mb=$(echo "$gpu_info" | cut -d'|' -f3)
    local os_info=$(detect_os)
    local os_id=$(echo "$os_info" | cut -d'|' -f1)
    local os_ver=$(echo "$os_info" | cut -d'|' -f2)
    local disk_gb=$(detect_disk)
    local deps_status=$(check_dependencies || true)
    local recommended_model=$(calculate_model "$ram_gb" "$gpu_type" "$vram_mb" "$cpu_cores")

    if [ "$OUTPUT_FORMAT" = "json" ]; then
        cat <<EOF
{
  "cpu": {
    "model": "$cpu_model",
    "cores": $cpu_cores
  },
  "ram_gb": $ram_gb,
  "gpu": {
    "type": "$gpu_type",
    "model": "$gpu_model",
    "vram_mb": $vram_mb
  },
  "os": {
    "id": "$os_id",
    "version": "$os_ver"
  },
  "disk_free_gb": $disk_gb,
  "dependencies": "$deps_status",
  "recommended_model": "$recommended_model",
  "install_size_gb": 2
}
EOF
    else
        echo "=== Hardware Detection ==="
        echo "CPU: $cpu_model ($cpu_cores cores)"
        echo "RAM: ${ram_gb}GB"
        echo "GPU: $gpu_type - $gpu_model (${vram_mb}MB VRAM)"
        echo "OS: $os_id $os_ver"
        echo "Disk: ${disk_gb}GB free"
        echo "Dependencies: $deps_status"
        echo "Recommended Model: $recommended_model"
    fi
}

main "$@"