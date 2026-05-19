# Architecture

## System Overview

Voice Agent is a production-ready voice AI system that processes audio through a pipeline:

```
Microphone → VAD → STT → LLM → TTS → Speaker
              ↓        ↓
          Silence   Tool Calling
          Detection    ↓
                     Shell/MCP
```

## Components

### Voice Loop (`baseline_loop.py`)

The main entry point. Orchestrates audio capture, transcription, response generation, and speech synthesis.

Key features:
- Queue-based architecture for non-blocking audio processing
- Energy-based VAD for voice detection
- Streaming LLM output for minimal latency
- Voice interrupt support

### VAD (Voice Activity Detection)

Energy-based detection using audio energy levels:

```python
SILENCE_THRESHOLD = 500  # energy level
SILENCE_FRAMES = 15      # frames of silence before end
```

When energy exceeds threshold, speech is detected. After speech ends (N frames of silence), transcription begins.

### STT (Speech-to-Text)

Uses Faster-Whisper for local transcription:
- Runs on CPU with INT8 quantization
- Small model for speed (singleton cached)
- ~580ms transcription time

### LLM (Language Model)

Ollama with qwen2.5:1.5b:
- Native tool calling via JSON
- Streaming responses for TTFT < 100ms
- Routes to appropriate model based on complexity

Model routing:
| Query Type | Model | Reasoning |
|------------|-------|-----------|
| Simple (time, weather) | qwen2.5:0.5b | Fast, < 0.1s TTFT |
| Medium (general chat) | qwen2.5:1.5b | Balance speed/capability |
| Complex (reasoning) | llama3.3:70b | Best quality |

### TTS (Text-to-Speech)

Kokoro-ONNX with GPU acceleration:
- AMD ROCm or NVIDIA CUDA support
- Real-time factor (RTF) < 0.3 on GPU
- 54 voices available

### LangGraph Agent (`langgraph_agent/`)

State machine for orchestration:

```
transcribe_node → route_node → respond_node → speak_node
```

Uses checkpointing for conversation memory.

## Data Flow

1. **Audio Capture**: Microphone records until silence detected
2. **VAD**: Energy threshold determines speech/silence
3. **STT**: Faster-Whisper converts audio → text
4. **LLM**: Ollama generates response (possibly with tool calls)
5. **Tool Execution**: Shell commands or MCP tools if needed
6. **TTS**: Kokoro converts text → audio
7. **Playback**: Audio played through speakers

## State Management

VoiceAgentState maintains:
- `conversation_history`: List of prior exchanges
- `current_task`: Current audio/text being processed
- `tool_results`: Results from any tool calls
- `interrupted`: Flag if user interrupted mid-response
- `response_text`: Generated response
- `route_target`: Which model/route to use

Checkpoints save state for recovery after interruption.

## Error Handling

All external calls (Ollama, TTS, audio) wrapped with:
- Connection error detection
- Timeout handling
- Graceful degradation
- User-friendly error messages

## Security

- Input validation on all text inputs
- Prompt injection sanitization
- PII redaction layer (email, phone, SSN, credit card)
- No external API calls (full data sovereignty)

## Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| TTFT | < 500ms | ~87ms |
| STT Latency | < 1s | ~580ms |
| TTS RTF | < 0.5 | ~0.24 |
| Concurrent Users | 20 | 20+ |

## File Structure

```
voice-agent/
├── baseline_loop.py      # Main voice pipeline
├── agent_server.py       # LiveKit bridge
├── langgraph_agent/     # LangGraph orchestration
│   ├── agent.py          # Graph definition
│   └── nodes.py          # Node implementations
├── supervisor.py         # Human-in-the-loop UI
├── benchmark.py          # 20-test benchmark suite
├── pii_handler.py       # PII detection/redaction
├── sip_bridge.py         # Asterisk integration
├── install.sh            # One-line installer
├── update.sh             # Update mechanism
├── requirements.txt      # Python dependencies
└── docs/                 # Documentation
```