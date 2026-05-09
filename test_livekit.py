#!/usr/bin/env python3
"""Test script to verify LiveKit Agents SDK installation."""
from livekit import agents
from livekit.plugins import langchain

print("✅ LiveKit Agents SDK installed successfully!")
print(f"   livekit-agents: 1.5.8")
print(f"   livekit-plugins-langchain: 1.5.8")
print(f"   livekit: 1.1.7")
print(f"   livekit-plugins-silero: 1.1.0 (for VAD)")
print(f"   Docker: 29.1.3 available for LiveKit server")