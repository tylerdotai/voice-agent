#!/usr/bin/env python3
"""
24-Hour Stability Test for Dexter Voice Agent.
Story 15: 24-Hour Stress Test.
"""
import time
import subprocess
import requests
import random
import os
from datetime import datetime

LOG_DIR = "/home/tyler/voice-agent/logs"
os.makedirs(LOG_DIR, exist_ok=True)

TEST_QUERIES = [
    "what time is it",
    "tell me a joke",
    "how are you",
    "what date is it",
    "hello",
]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(f"{LOG_DIR}/stress_test.log", "a") as f:
        f.write(line + "\n")

def check_ollama():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False
    except Exception:
        return False

def check_tts():
    try:
        from kokoro_onnx import Kokoro
        k = Kokoro("/home/tyler/kokoro-onnx/kokoro-v1.0.onnx", "/home/tyler/kokoro-onnx/voices-v1.0.bin")
        return True
    except ImportError:
        return False
    except Exception:
        return False

def run_test_query(query):
    start = time.time()
    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "qwen2.5:0.5b", "prompt": query, "stream": False},
            timeout=30
        )
        elapsed = time.time() - start
        return {"success": True, "latency": elapsed, "response": r.json().get("response","")[:50]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    log("Starting 24-hour stress test")
    log(f"Logging to {LOG_DIR}")
    
    start_time = time.time()
    test_count = 0
    success_count = 0
    
    while time.time() - start_time < 86400:  # 24 hours
        # Check systems
        if not check_ollama():
            log("ERROR: Ollama not responding")
            time.sleep(60)
            continue
        
        # Run test query
        query = random.choice(TEST_QUERIES)
        log(f"Test #{test_count}: '{query}'")
        
        result = run_test_query(query)
        test_count += 1
        
        if result.get("success"):
            success_count += 1
            log(f"  OK - {result['latency']:.2f}s - {result['response']}")
        else:
            log(f"  FAILED - {result.get('error')}")
        
        # Report every hour
        if test_count % 60 == 0:
            uptime_hours = (time.time() - start_time) / 3600
            success_rate = (success_count / test_count * 100) if test_count > 0 else 0
            log(f"STATUS: {uptime_hours:.1f}h | {test_count} tests | {success_rate:.1f}% success")
        
        time.sleep(60)  # Test every minute
    
    log("24-hour test complete!")
    log(f"Total: {test_count} tests, {success_count} successes")

if __name__ == "__main__":
    main()
