"""
Agent Server: Bridges LiveKit AgentSession events to LangGraph graph invocations.
Story 8: Connect LangGraph Agent to LiveKit Session.
"""
from livekit import agents
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins import openai
from langgraph_agent import create_voice_agent, VoiceAgentState

# Create LangGraph agent
graph_agent = create_voice_agent()

async def entrypoint(ctx: JobContext):
    """LiveKit agent entrypoint - connects to baseline voice loop."""
    print(f"Agent joining room: {ctx.room.name}")
    
    # State for conversation
    state = VoiceAgentState()
    
    async for audio_data in ctx.stream_incoming_audio():
        # Convert audio to text (placeholder)
        # In production: use faster-whisper here
        pass

def main():
    """Start the LiveKit agent worker."""
    WorkerOptions(
        entrypoint_fnc=entrypoint,
        model=openai.realtime.Model(
            model="gpt-4o-mini",
            instructions="You are Dexter, a helpful voice assistant."
        )
    ).start()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
