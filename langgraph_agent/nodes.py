"""Nodes for the voice agent graph."""
import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen2.5:0.5b"

def transcribe_node(state: VoiceAgentState) -> VoiceAgentState:
    """Transcribe audio to text."""
    # State.current_task contains the audio data from the loop
    # For now, assume it's pre-transcribed text in production
    return state

def route_node(state: VoiceAgentState) -> VoiceAgentState:
    """Route based on intent - simple vs complex."""
    text = state.current_task.lower()
    
    if any(word in text for word in ['hello', 'hi', 'hey', 'time', 'weather', 'joke']):
        state.route_target = "fast"
    elif any(word in text for word in ['search', 'find', 'look up', 'research']):
        state.route_target = "tools"
    else:
        state.route_target = "general"
    
    return state

def respond_node(state: VoiceAgentState) -> VoiceAgentState:
    """Generate response using Ollama."""
    prompt = f"You are a helpful voice assistant. Reply in 50 words or less. User said: {state.current_task}"
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        result = json.loads(response.text)
        state.response_text = result.get('response', '').strip()
    except Exception as e:
        state.response_text = "Sorry, I couldn't process that."
    
    return state

def speak_node(state: VoiceAgentState) -> VoiceAgentState:
    """Speak the response (placeholder - actual TTS happens in loop)."""
    print(f"Agent response: {state.response_text}")
    return state

# Story 17: Latency optimization - pre-warm model on startup
def prewarm_llm():
    """Pre-warm Ollama model with silent request."""
    try:
        requests.post(
            "http://localhost:11434/api/generate",
            json={"model": LLM_MODEL, "prompt": "ping", "stream": False},
            timeout=10
        )
        print("LLM pre-warmed")
    except Exception as e:
        print(f"Pre-warm failed: {e}")

# Story 18: A2A Protocol for multi-agent handoff
AGENT_CARD = {
    "name": "Dexter",
    "version": "1.0",
    "capabilities": ["voice", "stt", "tts", "tools"],
    "endpoint": "http://localhost:7880",
    "description": "Fully self-hosted voice agent on clawbox"
}

def a2a_handoff(task_description: str, target_agent: str = "supervisor") -> dict:
    """Handoff to another agent via A2A protocol."""
    return {
        "action": "handoff",
        "from": "dexter",
        "to": target_agent,
        "task": task_description,
        "agent_card": AGENT_CARD
    }
