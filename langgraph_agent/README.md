# LangGraph Voice Agent

## Overview
The voice agent uses LangGraph for orchestration with checkpoint-based fault tolerance.

## State Schema (VoiceAgentState)
- `conversation_history`: list of prior exchanges
- `current_task`: current user input
- `tool_results`: results from tool calls
- `interrupted`: flag for human-in-the-loop
- `response_text`: generated response

## Graph Nodes
1. **transcribe**: Convert audio → text
2. **route**: Intent detection (fast/tools/general)
3. **respond**: LLM inference via Ollama
4. **speak**: TTS playback

## Usage
```python
from langgraph_agent import VoiceAgent, VoiceAgentState

agent = create_voice_agent()
state = VoiceAgentState()
state.current_task = "hello"
result = agent.invoke(state)
```
