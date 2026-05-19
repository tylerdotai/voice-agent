<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template -->

<a id="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![Build][build-shield]][build-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/tylerdotai/voice-agent">
    <img src="logo.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Voice Agent</h3>

  <p align="center">
    Fully self-hosted voice AI agent — VAD, STT, LLM tool calling, and TTS running locally on CPU/GPU
    <br />
    <a href="https://github.com/tylerdotai/voice-agent/issues">Report Bug</a>
    ·
    <a href="https://github.com/tylerdotai/voice-agent/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#features">Features</a></li>
    <li><a href="#architecture">Architecture</a></li>
    <li><a href="#components">Components</a></li>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#benchmark">Benchmark</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

A production-ready, fully self-hosted voice AI agent built for local deployment. No cloud APIs, no data leaves your machine. Designed to run 24/7 on basic hardware with real-time voice command processing.

**Stack:** Faster-Whisper (STT) → Ollama (LLM with native tool calling) → Kokoro-ONNX (TTS) with LangGraph orchestration.

### Problem Solved
- Voice AI that respects privacy — all processing local
- Tool calling via native JSON (no MCP overhead for local shell access)
- Runs on basic hardware (8GB RAM, CPU or integrated GPU)
- Sub-second response for simple voice commands

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- FEATURES -->
## Features

### Voice Pipeline
- Energy-based VAD (Voice Activity Detection) with configurable silence threshold
- Faster-Whisper for local STT (no cloud dependency)
- Ollama LLM with streaming responses and native tool calling
- Kokoro-ONNX TTS with GPU acceleration (ROCm/CUDA)
- Voice interrupt — stop TTS mid-sentence by speaking

### Enterprise Readiness
- PII detection and redaction (email, phone, SSN, credit card)
- Audit logging with structured JSONL output
- Failover recovery for every component
- SLA compliance verification (20 concurrent users, <2s p99)
- Full data sovereignty — no external API calls required

### Benchmark Suite
- 20 automated tests across 5 tiers
- Component health, E2E pipeline, streaming TTFT, tool calling, multilingual, concurrent load, adversarial input
- Run with `python benchmark.py --verbose`

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ARCHITECTURE -->
## Architecture

```
Microphone → Energy VAD → Faster-Whisper STT → Ollama LLM (qwen2.5:1.5b)
                               ↓                    ↓
                         Silence Detection    Tool Calling / JSON
                                                  ↓
                                           Shell Tools / MCP
                                                  ↓
                            Kokoro-ONNX TTS ← Response Text
                               ↓
                         Audio Output
```

**Model Routing:**
| Model | Size | Speed | Use |
|-------|------|-------|-----|
| `qwen2.5:1.5b` | 986MB | ~145 tok/s | Default for voice (tool calling on CPU) |
| `smollm2:1.7b` | 1.8GB | ~134 tok/s | Medium complexity |
| `llama3.3:70b` | 42GB | ~10 tok/s | Complex reasoning (requires more RAM) |

**Ports:**
| Port | Service |
|------|---------|
| 11434 | Ollama |
| 7880 | LiveKit server (WebSocket) |
| 8888 | SearXNG (web search MCP) |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- COMPONENTS -->
## Components

| File | Purpose |
|------|---------|
| `baseline_loop.py` | Core voice pipeline — VAD → STT → LLM → TTS with interrupt handling |
| `langgraph_agent/` | LangGraph graph orchestration with state management |
| `supervisor.py` | Human-in-the-loop terminal UI |
| `benchmark.py` | 20-test benchmark suite across 5 tiers |
| `pii_handler.py` | PII detection and redaction (email, phone, SSN, credit card) |
| `failover_test.py` | Chaos engineering — component failure recovery tests |
| `agent_server.py` | LiveKit ↔ LangGraph bridge |
| `mcp_servers/` | MCP tool servers (searxng, filesystem, shell) |
| `livekit_server/` | Docker Compose for self-hosted LiveKit |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

- Python 3.12+
- Ollama running locally (`http://localhost:11434`)
- Kokoro ONNX model at `/home/tyler/kokoro-onnx/kokoro-v1.0.onnx`
- 8GB+ RAM for basic operation

### Installation

1. **Clone and enter the repo:**
   ```bash
   git clone https://github.com/tylerdotai/voice-agent.git
   cd voice-agent
   ```

2. **Create and activate venv:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   .venv/bin/pip install -r requirements.txt
   ```

4. **Pull the default model:**
   ```bash
   ollama pull qwen2.5:1.5b
   ```

5. **Run the voice agent:**
   ```bash
   .venv/bin/python baseline_loop.py
   ```

### Optional: Start LiveKit server
```bash
cd livekit_server && docker compose up -d
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE -->
## Usage

### Quick Start
```bash
# Run the voice agent
python baseline_loop.py

# Run benchmark suite
python benchmark.py --verbose

# Run specific tier
python benchmark.py --tier 3

# Run supervisor UI
python supervisor.py
```

### Systemd Service (24/7)
```bash
systemctl --user daemon-reload
systemctl --user enable voice-agent
systemctl --user start voice-agent
journalctl --user -u voice-agent -f
```

### VAD Configuration (baseline_loop.py)
```python
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500   # increase for louder environments
SILENCE_FRAMES = 15       # frames of silence before end-of-speech
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- BENCHMARK -->
## Benchmark

Run `python benchmark.py --verbose` for full output.

**Current: 19/20 passed | Avg Score: 106.2/100**

| Tier | Tests | Status |
|------|-------|--------|
| 1 | Component health (Ollama, STT, TTS, VAD) | 4/4 |
| 2 | Basic E2E (STT, LLM response, TTS) | 3/3 |
| 3 | Moderate (TTFT 87ms, tool calling, multilingual, memory) | 4/4 |
| 4 | Complex (noisy STT*, concurrent 20 users, long context, adversarial) | 3/4 |
| 5 | Enterprise (PII, audit, failover, SLA, data sovereignty) | 5/5 |

*Noisy Environment STT requires recorded audio samples in `logs/noisy_*.wav`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [x] VAD with voice interrupt
- [x] Faster-Whisper STT pipeline
- [x] Ollama LLM with streaming
- [x] Kokoro-ONNX TTS with GPU acceleration
- [x] Native tool calling (JSON)
- [x] PII redaction layer
- [x] Audit logging
- [x] Failover recovery
- [x] 20-user concurrent support
- [ ] Noisy environment STT (needs test audio samples)
- [ ] LiveKit WebRTC integration
- [ ] Multi-language TTS voices

See the [open issues](https://github.com/tylerdotai/voice-agent/issues) for full details.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

- **GitHub:** [tylerdotai/voice-agent](https://github.com/tylerdotai/voice-agent)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/badge/contributors-1-blue?style=for-the-badge
[contributors-url]: https://github.com/tylerdotai/voice-agent/graphs/contributors
[forks-shield]: https://img.shields.io/badge/forks-0-blue?style=for-the-badge
[forks-url]: https://github.com/tylerdotai/voice-agent/network/members
[stars-shield]: https://img.shields.io/badge/stars-0-blue?style=for-the-badge
[stars-url]: https://github.com/tylerdotai/voice-agent/stargazers
[issues-shield]: https://img.shields.io/badge/issues-0-blue?style=for-the-badge
[issues-url]: https://github.com/tylerdotai/voice-agent/issues
[license-shield]: https://img.shields.io/badge/license-MIT-blue?style=for-the-badge
[license-url]: https://github.com/tylerdotai/voice-agent/blob/main/LICENSE
[build-shield]: https://img.shields.io/badge/build-passing-brightgreen?style=for-the-badge
[build-url]: https://github.com/tylerdotai/voice-agent/actions