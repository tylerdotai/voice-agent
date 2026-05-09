#!/usr/bin/env python3
"""Story 1: LiveKit Agents SDK Echo Test
Verify LiveKit Agents SDK is properly installed.
"""

from livekit import api
from livekit.agents import Agent, AgentSession, JobContext, JobRequest
from livekit.plugins import openai
import sys

def test_livekit_imports():
    """Test that all LiveKit packages import correctly."""
    print("Testing LiveKit imports...")
    
    try:
        from livekit import api
        print("  ✓ livekit (core)")
        
        from livekit.agents import Agent, AgentSession, JobContext, JobRequest
        print("  ✓ livekit-agents")
        
        from livekit.plugins import openai
        print("  ✓ livekit-plugins-openai")
        
        from livekit.plugins import anthropic
        print("  ✓ livekit-plugins-anthropic")
        
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_livekit_api():
    """Test LiveKit API functionality."""
    print("\nTesting LiveKit API...")
    try:
        # Just verify the module is functional
        access_token = api.AccessToken("test_key", "test_secret")
        print("  ✓ AccessToken class available")
        return True
    except Exception as e:
        print(f"  ✗ API test failed: {e}")
        return False

def main():
    print("=" * 50)
    print("LiveKit Agents SDK Echo Test")
    print("=" * 50)
    
    results = []
    
    print("\n[1] Import Test")
    results.append(test_livekit_imports())
    
    print("\n[2] API Functionality Test")
    results.append(test_livekit_api())
    
    print("\n" + "=" * 50)
    if all(results):
        print("RESULT: All tests PASSED ✓")
        print("LiveKit Agents SDK is properly installed.")
        return 0
    else:
        print("RESULT: Some tests FAILED ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
