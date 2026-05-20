"""Voice Agent Graph using LangGraph."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .nodes import VoiceAgentState, transcribe_node, route_node, respond_node, speak_node


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
    VoiceAgent = builder.compile(checkpointer=checkpointer)

    return VoiceAgent
