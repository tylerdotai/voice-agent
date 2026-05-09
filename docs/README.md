# Dexter Voice Agent

A fully self-hosted local voice AI agent running 24/7 on clawbox.

## Quick Start

```bash
# Start the voice agent
python baseline_loop.py

# Or via systemd (24/7)
systemctl --user start voice-agent

# Run supervisor
python supervisor.py
```

## Architecture

- **STT**: Faster-Whisper small (CPU, ~0.6s)
- **LLM**: Ollama qwen2.5:0.5b (300 tok/s, <0.1s TTFT)
- **TTS**: Kokoro-ONNX (54 voices, ~1.3s generate)
- **Transport**: LiveKit WebRTC (self-hosted via Docker)

## Stories (18 total)

See `prd.json` for full story list.
