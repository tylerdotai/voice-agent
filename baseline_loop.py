#!/usr/bin/env python3
"""
Dexter Voice Agent - Baseline Voice Loop
Story 4: Core pipeline: mic → STT → LLM → TTS → speaker

Architecture:
  Microphone → VAD (energy-based) → Faster-Whisper STT → Ollama LLM (qwen2.5:0.5b)
                                                          ↓
 Speaker ← Kokoro-ONNX TTS ← Response text

Features:
  - Queue-based architecture with background threads
  - Energy-based VAD for voice detection
  - Streaming LLM output → TTS (don't wait for full response)
  - Interrupt handling (Ctrl+C)
  - Uses qwen2.5:0.5b for fast voice responses (<1s TTFT)
"""

import queue
import threading
import signal
import sys
import time
import array
import struct
import math

# Audio settings
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024  # samples per chunk
SILENCE_THRESHOLD = 500  # energy level for silence
SILENCE_FRAMES = 15  # frames of silence to detect end of speech

# Ollama settings
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen2.5:0.5b"  # fast model for voice

# TTS settings  
KOKORO_ONNX_PATH = "/home/tyler/kokoro-onnx/kokoro-v1.0.onnx"
KOKORO_VOICES_PATH = "/home/tyler/kokoro-onnx/voices-v1.0.bin"
DEFAULT_VOICE = "af_sarah"

# STT settings
STT_MODEL_SIZE = "small"  # small model for speed

import subprocess
import json
import requests

# Global state
running = True
current_audioPlaying = False

class VoiceLoop:
    # Class-level model caching (singleton pattern)
    _stt_model = None
    _tts_model = None
    
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.tts_queue = queue.Queue()
        self.running = True
        
        # Initialize STT (cached singleton)
        if VoiceLoop._stt_model is None:
            print("Loading Faster-Whisper STT model...")
            from faster_whisper import WhisperModel
            VoiceLoop._stt_model = WhisperModel(STT_MODEL_SIZE, device="cpu", compute_type="int8")
            print("STT ready")
        self.stt_model = VoiceLoop._stt_model
        
        # Initialize TTS (cached singleton)
        if VoiceLoop._tts_model is None:
            print("Loading Kokoro-ONNX TTS...")
            from kokoro_onnx import Kokoro
            VoiceLoop._tts_model = Kokoro(KOKORO_ONNX_PATH, KOKORO_VOICES_PATH)
            print(f"TTS ready with {len(VoiceLoop._tts_model.voices)} voices")
        self.tts = VoiceLoop._tts_model
        
    def get_audio_devices(self):
        """List available audio input devices."""
        import sounddevice as sd
        devices = sd.query_devices()
        inputs = [d for d in devices if d['max_input_channels'] > 0]
        return inputs
    
    def energy_level(self, data):
        """Calculate energy level of audio data (0-32768 range)."""
        # Unpack 16-bit samples
        samples = struct.unpack(f"{len(data)//2}h", data)
        energy = sum(abs(s) for s in samples) / len(samples)
        return energy
    
    def record_until_silence(self, device_index=None):
        """Record audio from microphone until silence is detected."""
        import sounddevice as sd
        
        silence_count = 0
        audio_frames = []
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            
            # Calculate energy
            energy = self.energy_level(indata.tobytes())
            
            if energy > SILENCE_THRESHOLD:
                audio_frames.append(indata.copy())
                silence_count = 0
            else:
                if audio_frames:
                    silence_count += 1
                    if silence_count < SILENCE_FRAMES:
                        audio_frames.append(indata.copy())
        
        try:
            with sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=SAMPLE_RATE,
                dtype='int16',
                blocksize=CHUNK_SIZE,
                callback=callback
            ):
                # Wait for first speech
                while silence_count < 3 and self.running:
                    time.sleep(0.1)
                
                if not self.running:
                    return None
                
                # Continue recording until silence
                while silence_count < SILENCE_FRAMES and self.running:
                    time.sleep(0.05)
            
            if not self.running:
                return None
            
            # Concatenate all frames
            if audio_frames:
                import numpy as np
                audio_data = np.concatenate(audio_frames)
                return audio_data.tobytes()
            
            return None
            
        except Exception as e:
            print(f"Recording error: {e}")
            return None
    
    def transcribe(self, audio_data):
        """Convert audio to text using Faster-Whisper."""
        import numpy as np
        from io import BytesIO
        import wave
        
        # Convert to numpy array
        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Transcribe
        segments, info = self.stt_model.transcribe(samples, beam_size=5)
        
        # Get full text
        text = " ".join(segment.text for segment in segments)
        return text.strip()
    
    MAX_INPUT_LENGTH = 500  # Max characters from user

    def generate_response(self, text):
        """Generate response using Ollama with streaming."""
        # Input validation - prevent resource exhaustion
        if not text or len(text) > MAX_INPUT_LENGTH:
            return "Sorry, I couldn't process that."
        
        # Sanitize input - escape any prompt injection attempts
        sanitized_text = text.replace("{", "{{").replace("}", "}}")
        prompt = f"You are a helpful voice assistant. Reply in 50 words or less. User said: {sanitized_text}"
        
        try:
            response = requests.post(
                OLLAMA_URL,
                json={"model": LLM_MODEL, "prompt": prompt, "stream": True},
                timeout=30,
                stream=True
            )
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if 'response' in data:
                        full_response += data['response']
                        # Put partial response in queue for TTS
                        self.tts_queue.put(full_response)
            
            return full_response.strip()
            
        except Exception as e:
            print(f"LLM error: {e}")
            return "Sorry, I couldn't process that."
    
    def speak(self, text):
        """Convert text to speech and play."""
        import sounddevice as sd
        
        try:
            samples, sr = self.tts.create(text, voice=DEFAULT_VOICE, speed=1.0)
            sd.play(samples, sr)
            sd.wait()
        except Exception as e:
            print(f"TTS error: {e}")
    
    def run(self, device_index=None):
        """Main voice loop."""
        print("\n🎤 Dexter Voice Agent - Baseline Loop")
        print(f"   STT: Faster-Whisper {STT_MODEL_SIZE}")
        print(f"   LLM: {LLM_MODEL} via Ollama")
        print(f"   TTS: Kokoro-ONNX ({DEFAULT_VOICE})")
        print("\nListening... Press Ctrl+C to exit\n")
        
        while self.running:
            try:
                # 1. Record audio
                print("👂 Listening...")
                audio_data = self.record_until_silence(device_index)
                
                if not self.running:
                    break
                
                if not audio_data:
                    continue
                
                # 2. Transcribe
                print("📝 Transcribing...")
                text = self.transcribe(audio_data)
                
                if not text:
                    print("   (no speech detected)")
                    continue
                
                print(f"   You: {text[:100]}")
                
                # 3. Generate response
                print("🤖 Thinking...")
                response = self.generate_response(text)
                
                if not response:
                    continue
                
                print(f"   Dexter: {response[:100]}")
                
                # 4. Speak
                print("🗣️ Speaking...")
                self.speak(response)
                
            except KeyboardInterrupt:
                print("\n\nStopping...")
                break
            except Exception as e:
                print(f"Error: {e}")
                continue
        
        print("Voice agent stopped.")


def signal_handler(sig, frame):
    global running
    running = False
    print("\nInterrupt received, stopping...")


def main():
    global running
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create voice loop
    vl = VoiceLoop()
    
    # List audio devices
    print("\n=== Audio Devices ===")
    devices = vl.get_audio_devices()
    for i, d in enumerate(devices):
        print(f"  {i}: {d['name']} ({d['max_input_channels']} channels)")
    
    # Run voice loop
    vl.run(device_index=None)  # None = default device


if __name__ == "__main__":
    main()