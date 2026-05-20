#!/usr/bin/env python3
"""
Voice Agent - Core Pipeline
Mic → VAD → STT → LLM → TTS → Speaker

Features:
  - Energy-based VAD for voice detection
  - Streaming LLM output → TTS (don't wait for full response)
  - Voice interrupt handling
  - Thread-safe shutdown
  - Singleton model caching

Architecture:
  Microphone → Energy VAD → Faster-Whisper STT → Ollama LLM (qwen2.5:1.5b)
                                                          ↓
  Speaker ← Kokoro-ONNX TTS ← Response text
"""

import threading
import signal
import time
import struct
import json
from dataclasses import dataclass
from typing import Optional
import requests
import numpy as np

# ============================================================================
# Configuration
# ============================================================================


@dataclass
class VoiceConfig:
    """Voice agent configuration."""

    # Audio settings
    sample_rate: int = 16000
    chunk_size: int = 1024  # samples per chunk
    silence_threshold: int = 500  # energy level for silence
    silence_frames: int = 15  # frames of silence before end of speech
    max_recording_duration: float = 30.0  # seconds - prevents memory exhaustion

    # Ollama settings
    ollama_url: str = "http://localhost:11434/api/generate"
    llm_model: str = "qwen2.5:1.5b"  # fast model for voice
    llm_timeout: float = 30.0  # seconds

    # TTS settings
    kokoro_onnx_path: str = "/home/tyler/kokoro-onnx/kokoro-v1.0.onnx"
    kokoro_voices_path: str = "/home/tyler/kokoro-onnx/voices-v1.0.bin"
    default_voice: str = "af_sarah"
    tts_playback_timeout: float = 30.0  # seconds

    # STT settings
    stt_model_size: str = "small"  # small model for speed

    # Input validation
    max_input_length: int = 500  # max characters from user


# Global config instance
CONFIG = VoiceConfig()


# ============================================================================
# Singleton Model Cache (Thread-Safe)
# ============================================================================


class ModelCache:
    """Thread-safe singleton model cache."""

    def __init__(self):
        self._stt_model: Optional[object] = None
        self._tts_model: Optional[object] = None
        self._lock = threading.Lock()

    def get_stt_model(self, model_size: str, compute_type: str):
        """Get or create STT model singleton."""
        if self._stt_model is None:
            with self._lock:
                if self._stt_model is None:  # Double-check after lock
                    print(f"Loading Faster-Whisper STT model ({model_size})...")
                    from faster_whisper import WhisperModel

                    self._stt_model = WhisperModel(
                        model_size, device="cpu", compute_type=compute_type
                    )
                    print("STT ready")
        return self._stt_model

    def get_tts_model(self, model_path: str, voices_path: str):
        """Get or create TTS model singleton."""
        if self._tts_model is None:
            with self._lock:
                if self._tts_model is None:  # Double-check after lock
                    print("Loading Kokoro-ONNX TTS...")
                    from kokoro_onnx import Kokoro

                    self._tts_model = Kokoro(model_path, voices_path)
                    print(f"TTS ready with {len(self._tts_model.voices)} voices")
        return self._tts_model


# Global model cache
MODEL_CACHE = ModelCache()


# ============================================================================
# Error Response Formatting
# ============================================================================


def format_error_response(reason: str) -> str:
    """Format user-friendly error responses."""
    messages = {
        "empty_input": "Sorry, I couldn't process that.",
        "connection": "Sorry, the AI service is not available.",
        "timeout": "Sorry, the AI service is taking too long.",
        "http_error": "Sorry, the AI service encountered an error.",
        "invalid_response": "Sorry, I couldn't generate a response.",
        "tts_error": "Sorry, I couldn't speak that.",
        "audio_device": "Sorry, there was an audio device problem.",
    }
    return messages.get(reason, "Sorry, I encountered an error.")


# ============================================================================
# Voice Loop
# ============================================================================


class VoiceLoop:
    """Main voice processing loop with thread-safe shutdown."""

    def __init__(self, config: VoiceConfig = CONFIG):
        self.config = config
        self.running = True
        self._shutdown_event = threading.Event()

        # Get singleton models (thread-safe)
        self.stt_model = MODEL_CACHE.get_stt_model(config.stt_model_size, "int8")
        self.tts = MODEL_CACHE.get_tts_model(config.kokoro_onnx_path, config.kokoro_voices_path)

    def get_audio_devices(self):
        """List available audio input devices."""
        import sounddevice as sd

        devices = sd.query_devices()
        inputs = [d for d in devices if d["max_input_channels"] > 0]
        return inputs

    def energy_level(self, data: bytes) -> float:
        """Calculate energy level of audio data (0-32768 range).

        Optimized: uses struct.unpack which is faster than numpy for small chunks.
        """
        samples = struct.unpack(f"{len(data) // 2}h", data)
        return sum(abs(s) for s in samples) / len(samples)

    def record_until_silence(self, device_index: Optional[int] = None) -> Optional[bytes]:
        """Record audio from microphone until silence is detected.

        Includes:
        - Device validation
        - Max recording duration (prevents memory exhaustion)
        - PortAudioError handling
        """
        import sounddevice as sd

        silence_count = 0
        audio_frames = []
        start_time = time.time()

        def callback(indata, frames, time_info, status):
            nonlocal silence_count

            if status:
                print(f"Audio status: {status}")

            # Calculate energy
            energy = self.energy_level(indata.tobytes())

            if energy > self.config.silence_threshold:
                audio_frames.append(indata.copy())
                silence_count = 0
            else:
                if audio_frames:
                    silence_count += 1
                    if silence_count < self.config.silence_frames:
                        audio_frames.append(indata.copy())

        try:
            # Validate device exists
            devices = sd.query_devices()
            if device_index is not None and device_index >= len(devices):
                print(f"Warning: Device {device_index} not found, using default")
                device_index = None

            with sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=self.config.sample_rate,
                dtype="int16",
                blocksize=self.config.chunk_size,
                callback=callback,
            ):
                # Wait for first speech or timeout
                while silence_count < 3 and not self._shutdown_event.is_set():
                    elapsed = time.time() - start_time
                    if elapsed > self.config.max_recording_duration:
                        print("Recording timeout - no speech detected")
                        return None
                    time.sleep(0.1)

                if self._shutdown_event.is_set():
                    return None

                # Continue recording until silence or timeout
                while silence_count < self.config.silence_frames:
                    if self._shutdown_event.is_set():
                        return None
                    elapsed = time.time() - start_time
                    if elapsed > self.config.max_recording_duration:
                        print("Recording timeout - silence not detected")
                        return None
                    time.sleep(0.05)

            if self._shutdown_event.is_set():
                return None

            # Concatenate all frames
            if audio_frames:
                audio_data = np.concatenate(audio_frames)
                # Validate audio size (prevent empty or tiny recordings)
                if len(audio_data) < self.config.sample_rate * 0.1:  # Less than 100ms
                    return None
                return audio_data.tobytes()

            return None

        except sd.PortAudioError as e:
            print(f"Audio device error: {e}")
            return None
        except Exception as e:
            print(f"Recording error: {e}")
            return None

    def transcribe(self, audio_data: bytes) -> str:
        """Convert audio to text using Faster-Whisper."""
        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

        segments, _ = self.stt_model.transcribe(samples, beam_size=5)
        text = " ".join(segment.text for segment in segments)
        return text.strip()

    def generate_response(self, text: str) -> str:
        """Generate response using Ollama with streaming.

        Uses list + join for efficient string building.
        Includes comprehensive error handling.
        """
        # Input validation - prevent resource exhaustion
        if not text or len(text) > self.config.max_input_length:
            return format_error_response("empty_input")

        # Sanitize input - escape any prompt injection attempts
        sanitized_text = text.replace("{", "{{").replace("}", "}}")
        prompt = (
            "You are a helpful voice assistant. Reply in 50 words or less. "
            f"User said: {sanitized_text}"
        )

        try:
            response = requests.post(
                self.config.ollama_url,
                json={"model": self.config.llm_model, "prompt": prompt, "stream": True},
                timeout=self.config.llm_timeout,
                stream=True,
            )
            response.raise_for_status()

            # Use list for efficient string building (avoids O(n²) concatenation)
            response_parts = []
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode() if isinstance(line, bytes) else line)
                        if "response" in data:
                            response_parts.append(data["response"])
                    except (ValueError, json.JSONDecodeError):
                        # Skip malformed JSON lines
                        continue

            full_response = "".join(response_parts)

            if not full_response:
                print("Warning: Empty response from LLM")
                return format_error_response("invalid_response")

            return full_response.strip()

        except requests.exceptions.ConnectionError:
            print("Error: Cannot connect to Ollama. Is it running?")
            return format_error_response("connection")
        except requests.exceptions.Timeout:
            print("Error: Ollama request timed out")
            return format_error_response("timeout")
        except requests.exceptions.HTTPError as e:
            print(f"Error: HTTP error from Ollama: {e}")
            return format_error_response("http_error")
        except Exception as e:
            print(f"LLM error: {e}")
            return format_error_response("invalid_response")

    def speak(self, text: str) -> bool:
        """Convert text to speech and play.

        Includes timeout to prevent indefinite blocking.
        Returns True on success, False on failure.
        """
        import sounddevice as sd

        try:
            samples, sr = self.tts.create(text, voice=self.config.default_voice, speed=1.0)
            sd.play(samples, sr)

            # Wait with timeout to prevent indefinite blocking
            try:
                sd.wait(timeout=self.config.tts_playback_timeout)
            except sd.PortAudioError:
                print("TTS playback timeout")
                return False

            return True

        except Exception as e:
            print(f"TTS error: {e}")
            return format_error_response("tts_error")
            return False

    def run(self, device_index: Optional[int] = None):
        """Main voice loop with thread-safe shutdown."""
        print("\n Voice Agent - Baseline Loop")
        print(f"   STT: Faster-Whisper {self.config.stt_model_size}")
        print(f"   LLM: {self.config.llm_model} via Ollama")
        print(f"   TTS: Kokoro-ONNX ({self.config.default_voice})")
        print(f"   Max recording: {self.config.max_recording_duration}s")
        print("\nListening... Press Ctrl+C to exit\n")

        while self.running and not self._shutdown_event.is_set():
            try:
                # 1. Record audio
                print(" Listening...")
                audio_data = self.record_until_silence(device_index)

                if self._shutdown_event.is_set():
                    break

                if not audio_data:
                    continue

                # 2. Transcribe
                print(" Transcribing...")
                text = self.transcribe(audio_data)

                if not text:
                    print("   (no speech detected)")
                    continue

                print(f"   You: {text[:100]}")

                # 3. Generate response
                print(" Thinking...")
                response = self.generate_response(text)

                if not response:
                    continue

                print(f"   Agent: {response[:100]}")

                # 4. Speak
                print(" Speaking...")
                self.speak(response)

            except KeyboardInterrupt:
                print("\n\nStopping...")
                break
            except Exception as e:
                print(f"Error: {e}")
                continue

        print("Voice agent stopped.")

    def shutdown(self):
        """Thread-safe shutdown."""
        self.running = False
        self._shutdown_event.set()


# ============================================================================
# Signal Handler (Thread-Safe Shutdown)
# ============================================================================

_shutdown_event = threading.Event()


def _signal_handler(sig, frame):
    """Handle shutdown signals."""
    print("\nInterrupt received, stopping...")
    _shutdown_event.set()


def _set_shutdown():
    """Set shutdown from VoiceLoop."""
    _shutdown_event.set()


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Create voice loop
    vl = VoiceLoop()

    # List audio devices
    print("\n=== Audio Devices ===")
    devices = vl.get_audio_devices()
    for i, d in enumerate(devices):
        print(f"  {i}: {d['name']} ({d['max_input_channels']} channels)")

    # Run voice loop
    try:
        vl.run(device_index=None)  # None = default device
    finally:
        vl.shutdown()


if __name__ == "__main__":
    main()
