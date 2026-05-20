"""
A2A (Agent-to-Agent) Protocol Implementation
Story 18: Multi-Agent Handoff Support
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentCard:
    name: str
    version: str
    capabilities: list
    endpoint: str
    description: str


@dataclass
class A2AMessage:
    action: str
    from_agent: str
    to_agent: str
    task: str
    payload: Optional[dict] = None


class A2AServer:
    """Simple A2A server for agent communication."""

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.agents = {agent_card.name: agent_card}

    def register(self, card: AgentCard):
        self.agents[card.name] = card

    def send(self, message: A2AMessage) -> dict:
        """Send message to target agent."""
        if message.to_agent not in self.agents:
            return {"error": f"Unknown agent: {message.to_agent}"}
        # In production: route to actual agent
        return {"status": "forwarded", "to": message.to_agent}


# Agent card for Dexter
DEXTER_CARD = AgentCard(
    name="Dexter",
    version="1.0",
    capabilities=["voice", "stt", "tts", "search", "files", "time"],
    endpoint="http://localhost:7880",
    description="Local voice agent on clawbox, AMD Ryzen AI MAX+ 395",
)

if __name__ == "__main__":
    server = A2AServer(DEXTER_CARD)
    print("A2A Server initialized")
    print(f"Agent: {DEXTER_CARD.name} at {DEXTER_CARD.endpoint}")
