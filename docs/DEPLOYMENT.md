# Deployment Guide

## Prerequisites

- Linux host, preferably Ubuntu 22.04/24.04
- Python 3.12+
- Ollama reachable at `http://localhost:11434`
- Default verified model: `qwen2.5:1.5b`
- Microphone and speakers for local voice-loop use, or SIP/phone input for telephony integration
- Kokoro ONNX files available locally:
  - model: `/home/tyler/kokoro-onnx/kokoro-v1.0.onnx`
  - voices: `/home/tyler/kokoro-onnx/voices-v1.0.bin`

### Hardware Requirements

| Profile | CPU | RAM | Disk | Notes |
|---------|-----|-----|------|-------|
| Minimum | 4 cores | 8GB | 10GB free | Basic local voice loop with small local models |
| Recommended | 8+ cores | 16GB+ | 20GB+ free | Better latency headroom and smoother TTS/STT |
| Optional GPU | AMD or NVIDIA | 16GB+ system RAM | 20GB+ free | Helps TTS acceleration; CPU-only still works |

A practical SMB box is a mini PC / NUC-style machine with Ubuntu 24.04, 16GB RAM, 4–8 CPU cores, and 20GB+ free disk.

Optional:
- GPU (NVIDIA or AMD) for faster TTS
- Asterisk/FreePBX for phone integration
- SIP support may require system-level PJSIP build prerequisites because `requirements.txt` includes `pjsua2`.

## Installation Methods

### 1. One-Line Installer

```bash
curl -fsSL https://install.voice-agent.local | bash
```

The installer will:
- Detect your hardware
- Install Ollama (if not present)
- Create Python virtual environment
- Install dependencies
- Pull appropriate model
- Create systemd service

### 2. Docker Compose

```bash
git clone https://github.com/tylerdotai/voice-agent.git
cd voice-agent
docker compose up -d
```

This starts:
- `ollama` - LLM inference server
- `voice-agent` - Main application
- `livekit` - WebRTC server (optional)
- `searxng` - Web search (optional)

### 3. Manual Installation

```bash
# Install system deps
sudo apt-get update
sudo apt-get install -y curl python3 python3-venv

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sudo sh

# Clone and setup
git clone https://github.com/tylerdotai/voice-agent.git
cd voice-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Pull model
ollama pull qwen2.5:1.5b

# Run
.venv/bin/python baseline_loop.py
```

## Systemd Service (24/7)

After installation, you can run as a service:

```bash
systemctl --user daemon-reload
systemctl --user enable voice-agent
systemctl --user start voice-agent
systemctl --user status voice-agent
```

View logs:
```bash
journalctl --user -u voice-agent -f
```

## Hardware Detection

The installer auto-detects hardware and selects appropriate model:

| Hardware | Recommended Model |
|----------|-------------------|
| NVIDIA 12GB+ VRAM | qwen2.5:3b |
| AMD 8GB+ VRAM | qwen2.5:3b |
| 32GB+ RAM | qwen2.5:1.5b |
| 16GB RAM | qwen2.5:1.5b |
| 8GB RAM | qwen2.5:0.5b |
| <8GB RAM | smollm2:360m |

To manually detect hardware:
```bash
./scripts/detect_hardware.sh
```

## Updates

Update to latest version:
```bash
./update.sh
```

This will:
- Backup configuration
- Pull latest from git
- Update Python dependencies
- Update Ollama models
- Run benchmark verification
- Restart service

## Backup and Restore

Backup configuration:
```bash
./scripts/backup_config.sh
```

Restore from backup:
```bash
./scripts/restore_config.sh /path/to/backup.tar.gz
```

## Network Configuration

### Ports

| Port | Service | Description |
|------|---------|-------------|
| 11434 | Ollama | LLM API |
| 7880 | LiveKit | WebSocket for voice |
| 8888 | SearXNG | Web search MCP |

### Firewall

If using firewall, allow these ports:
```bash
sudo ufw allow 11434/tcp
sudo ufw allow 7880/tcp
sudo ufw allow 8888/tcp
```

## Production Checklist

- [ ] Ollama is running (`pgrep -x ollama`)
- [ ] Model is available (`ollama list`)
- [ ] Microphone is working
- [ ] TTS is working (run test)
- [ ] Benchmark passes (`.venv/bin/python benchmark.py`)
- [ ] Service is enabled for auto-start (`systemctl enable voice-agent`)
