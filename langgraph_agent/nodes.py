"""Nodes for the voice agent graph."""
import requests
import json
from dataclasses import dataclass

OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen2.5:1.5b"  # Must match baseline_loop.py


def format_error_response(reason: str) -> str:
    """Format user-friendly error responses."""
    messages = {
        "connection": "Sorry, the AI service is not available.",
        "timeout": "Sorry, the AI service is taking too long.",
        "invalid_data": "Sorry, the AI service returned invalid data.",
        "unknown": "Sorry, I encountered an error.",
    }
    return messages.get(reason, messages["unknown"])

class VoiceAgentState:
    """State schema for the voice agent graph."""
    def __init__(self):
        self.conversation_history: list = []
        self.current_task: str = ""
        self.tool_results: dict = {}
        self.interrupted: bool = False
        self.response_text: str = ""
        self.route_target: str = "general"

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
        response.raise_for_status()
        result = json.loads(response.text)
        state.response_text = result.get('response', '').strip()

        if not state.response_text:
            print("Warning: Empty response from LLM")
            state.response_text = format_error_response("unknown")

    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama")
        state.response_text = format_error_response("connection")
    except requests.exceptions.Timeout:
        print("Error: Ollama request timed out")
        state.response_text = format_error_response("timeout")
    except json.JSONDecodeError as e:
        print(f"Error: Malformed JSON from Ollama: {e}")
        state.response_text = format_error_response("invalid_data")
    except Exception as e:
        print(f"Unexpected error in respond_node: {e}")
        state.response_text = format_error_response("unknown")

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
