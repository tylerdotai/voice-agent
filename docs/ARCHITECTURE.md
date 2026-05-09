# Dexter Voice Agent - Architecture

## Core Pipeline

```
User speaks → Energy VAD → Faster-Whisper STT → Ollama LLM → Kokoro TTS → User hears
                      ↓              ↓              ↓
                   Silence       qwen2.5:0.5b   54 voices
                   detection      or smollm2:1.7b
                                 or MiniMax API
```

## Components

1. **baseline_loop.py** - Core voice pipeline (Stories 4, 5)
2. **langgraph_agent/** - Agent orchestration with checkpointing (Story 7)
3. **agent_server.py** - LiveKit ↔ LangGraph bridge (Story 8)
4. **mcp_servers/** - Tool servers (SearXNG, Filesystem, Shell) (Story 10)
5. **supervisor.py** - Human-in-the-loop UI (Story 12)
6. **livekit_server/** - Self-hosted LiveKit WebRTC server (Story 6)
7. **voice-agent.service** - Systemd service for 24/7 (Story 14)
8. **stress_test.py** - 24-hour stability test (Story 15)
