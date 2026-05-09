#!/usr/bin/env python3
"""Test script to verify LiveKit Agents SDK installation."""

import sys


def test_livekit_import():
    """Test that LiveKit modules can be imported."""
    try:
        from livekit import api
        print("✓ LiveKit API imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import LiveKit API: {e}")
        return False
    return True


def test_agents_import():
    """Test that LiveKit Agents can be imported."""
    try:
        from livekit.agents import Agent, AgentSession, function_tool
        print("✓ LiveKit Agents core imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import LiveKit Agents: {e}")
        return False
    return True


def test_plugins_import():
    """Test that LiveKit plugins can be imported."""
    try:
        from livekit.plugins import langchain
        print("✓ LiveKit langchain plugin imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import LiveKit langchain plugin: {e}")
        return False
    return True


def main():
    """Run all LiveKit tests."""
    print("Testing LiveKit Agents SDK Installation")
    print("=" * 40)
    
    results = [
        test_livekit_import(),
        test_agents_import(),
        test_plugins_import(),
    ]
    
    print("=" * 40)
    if all(results):
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
