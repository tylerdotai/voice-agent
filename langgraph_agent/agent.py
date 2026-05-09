"""Voice Agent Graph using LangGraph."""
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

class VoiceAgentState:
    """State schema for the voice agent graph."""
    def __init__(self):
        self.conversation_history: list = []
        self.current_task: str = ""
        self.tool_results: dict = {}
        self.interrupted: bool = False
        self.response_text: str = ""

def create_voice_agent():
    """Create and compile the voice agent graph."""
    builder = StateGraph(VoiceAgentState)
    
    # Add nodes
    builder.add_node("transcribe", transcribe_node)
    builder.add_node("route", route_node)
    builder.add_node("respond", respond_node)
    builder.add_node("speak", speak_node)
    
    # Set entry point
    builder.set_entry_point("transcribe")
    
    # Add edges
    builder.add_edge("transcribe", "route")
    builder.add_edge("route", "respond")
    builder.add_edge("respond", "speak")
    builder.add_edge("speak", END)
    
    # Compile with checkpointing
    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
