# Voice Agent Documentation

## Overview

Voice Agent is a fully self-hosted voice AI system with VAD, STT, LLM, and TTS running locally. No cloud APIs required.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/tylerdotai/voice-agent.git
cd voice-agent

# Install (one command)
curl -fsSL https://install.voice-agent.local | bash

# Or with Docker
docker compose up -d
```

## Architecture

```
Microphone → Energy VAD → Faster-Whisper STT → Ollama LLM → Kokoro-ONNX TTS → Speaker
                        ↓                        ↓
                   Silence Detection       Tool Calling (JSON)
                                                  ↓
                                           Shell / MCP Tools
```

## Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| VAD | Energy-based | Voice activity detection |
| STT | Faster-Whisper | Speech to text |
| LLM | Ollama + qwen2.5:1.5b | Language model with tool calling |
| TTS | Kokoro-ONNX | Text to speech with GPU acceleration |

## Installation

### Manual Installation

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y curl python3 python3-venv

# 2. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sudo sh

# 3. Clone and setup
git clone https://github.com/tylerdotai/voice-agent.git
cd voice-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Pull model
ollama pull qwen2.5:1.5b

# 5. Run
python baseline_loop.py
```

### Docker Installation

```bash
docker compose up -d
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `KOKORO_ONNX_PATH` | `/home/tyler/kokoro-onnx/kokoro-v1.0.onnx` | TTS model path |
| `KOKORO_VOICES_PATH` | `/home/tyler/kokoro-onnx/voices-v1.0.bin` | Voices file |
| `VOICE_AGENT_MODEL` | `qwen2.5:1.5b` | LLM model |
| `SAMPLE_RATE` | `16000` | Audio sample rate |
| `SILENCE_THRESHOLD` | `500` | VAD energy threshold |
| `SILENCE_FRAMES` | `15` | Silence frames before end |

## Troubleshooting

### Ollama not running

```bash
ollama serve &
```

### Check model is available

```bash
ollama list
```

### View logs

```bash
journalctl --user -u voice-agent -f
```

## License

MIT