#!/usr/bin/env python3
"""
SIP Bridge - Connects voice agent to phone lines via Asterisk/FreePBX
Handles inbound calls, pipes audio through the voice pipeline, returns TTS

For SMBs with existing phone systems - just connect to their Asterisk box.
"""

import asyncio
import socket
import json
import wave
import struct
import logging
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import required libs, graceful degradation
try:
    import pjsua2 as pj
    PJSIP_AVAILABLE = True
except ImportError:
    PJSIP_AVAILABLE = False
    logger.warning("pjsua2 not available - SIP bridge will run in passthrough mode")

try:
    from asterisk.asterisk import AsteriskManager
    AST_MANAGER_AVAILABLE = True
except ImportError:
    AST_MANAGER_AVAILABLE = False


class CallState(Enum):
    """SIP call states"""
    IDLE = "idle"
    RINGING = "ringing"
    CONNECTED = "connected"
    TALKING = "talking"
    HANGUP = "hangup"


@dataclass
class CallConfig:
    """Configuration for SIP bridge"""
    asterisk_host: str = "localhost"
    asterisk_port: int = 5038
    asterisk_user: str = "voiceagent"
    asterisk_password: str = "secret"
    sip_extension: str = "6000"
    sip_password: str = ""
    context: str = "voice-agent"
    audio_sample_rate: int = 8000
    max_call_duration_seconds: int = 600


class AudioBuffer:
    """Ring buffer for audio streaming"""
    def __init__(self, max_size: int = 16000):
        self.buffer = bytearray()
        self.max_size = max_size

    def write(self, audio_data: bytes) -> None:
        self.buffer.extend(audio_data)
        if len(self.buffer) > self.max_size:
            self.buffer = self.buffer[-self.max_size:]

    def read(self, size: int) -> bytes:
        if len(self.buffer) < size:
            result = bytes(self.buffer)
            self.buffer.clear()
            return result
        result = bytes(self.buffer[:size])
        self.buffer = self.buffer[size:]
        return result

    def clear(self) -> None:
        self.buffer.clear()


class SIPBridge:
    """
    SIP Bridge for connecting phone calls to the voice agent pipeline.

    Connects to Asterisk via AMI (Asterisk Manager Interface) for call control,
    and handles RTP audio streaming directly.

    Usage:
        bridge = SIPBridge(config)
        await bridge.start()
        # Calls come in, get processed, TTS returned
        await bridge.stop()
    """

    def __init__(self, config: Optional[CallConfig] = None):
        self.config = config or CallConfig()
        self.running = False
        self.active_calls: dict[str, CallState] = {}
        self.audio_buffers: dict[str, AudioBuffer] = {}

        # Voice pipeline integration
        self.voice_pipeline: Optional[Callable] = None

        # AMI socket
        self.ami_socket: Optional[socket.socket] = None

    def set_voice_pipeline(self, pipeline_fn: Callable) -> None:
        """Set the voice pipeline function to process audio"""
        self.voice_pipeline = pipeline_fn

    async def connect_ami(self) -> bool:
        """Connect to Asterisk Manager Interface"""
        try:
            self.ami_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ami_socket.settimeout(10)
            self.ami_socket.connect((
                self.config.asterisk_host,
                self.config.asterisk_port
            ))

            # Read initial greeting
            greeting = self.ami_socket.recv(1024).decode()
            logger.info(f"AMI connected: {greeting[:50]}")

            # Login
            login_cmd = f"Action: Login\r\nUsername: {self.config.asterisk_user}\r\nSecret: {self.config.asterisk_password}\r\n\r\n"
            self.ami_socket.send(login_cmd.encode())

            response = self.ami_socket.recv(1024).decode()
            if "Success" in response:
                logger.info("AMI login successful")
                return True
            else:
                logger.error(f"AMI login failed: {response}")
                return False

        except Exception as e:
            logger.error(f"AMI connection failed: {e}")
            return False

    async def disconnect_ami(self) -> None:
        """Disconnect from AMI"""
        if self.ami_socket:
            try:
                self.ami_socket.send(b"Action: Logoff\r\n\r\n")
                self.ami_socket.close()
            except:
                pass
            self.ami_socket = None

    async def send_ami_command(self, command: str) -> dict:
        """Send AMI command and return parsed response"""
        try:
            self.ami_socket.send(command.encode())
            response = b""
            while True:
                chunk = self.ami_socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"\r\n\r\n" in response:
                    break

            # Parse response into dict
            result = {}
            for line in response.decode().split("\r\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    result[key.strip()] = value.strip()
            return result

        except Exception as e:
            logger.error(f"AMI command failed: {e}")
            return {"Response": "Error", "Message": str(e)}

    async def originate_call(self, destination: str) -> Optional[str]:
        """Originate an outbound call"""
        command = (
            f"Action: Originate\r\n"
            f"Channel: SIP/{self.config.sip_extension}\r\n"
            f"Context: {self.config.context}\r\n"
            f"Exten: {destination}\r\n"
            f"Priority: 1\r\n"
            f"Timeout: 30000\r\n\r\n"
        )
        result = await self.send_ami_command(command)
        return result.get("UniqueID")

    async def handle_inbound_call(self, call_id: str, caller: str) -> None:
        """Handle an inbound call - process through voice pipeline"""
        logger.info(f"Inbound call from {caller}: {call_id}")

        self.active_calls[call_id] = CallState.RINGING
        self.audio_buffers[call_id] = AudioBuffer()

        try:
            # Answer the call
            await self.send_ami_command(
                f"Action: Hangup\r\nChannel: {call_id}\r\n\r\n"
            )

            # In a real implementation, we'd:
            # 1. Accept the call
            # 2. Start RTP audio streaming
            # 3. Feed audio to voice pipeline
            # 4. Return TTS audio

            # For now, mark as connected
            self.active_calls[call_id] = CallState.CONNECTED

            # Simulate call processing
            # In production, this would:
            # - Open RTP socket
            # - Stream audio bidirectionally
            # - Run VAD/STT/LLM/TTS pipeline

            await asyncio.sleep(5)  # Placeholder for actual processing

            # Hangup
            self.active_calls[call_id] = CallState.HANGUP
            logger.info(f"Call {call_id} completed")

        except Exception as e:
            logger.error(f"Call handling error for {call_id}: {e}")
            self.active_calls[call_id] = CallState.HANGUP

        finally:
            # Cleanup
            if call_id in self.audio_buffers:
                del self.audio_buffers[call_id]

    async def start(self) -> bool:
        """Start the SIP bridge"""
        logger.info("Starting SIP bridge...")

        if not self.connect_ami():
            logger.warning("AMI connection failed - running in passthrough mode")
            return False

        self.running = True

        # Start AMI event listener in background
        asyncio.create_task(self._ami_event_loop())

        logger.info(f"SIP bridge started on extension {self.config.sip_extension}")
        return True

    async def _ami_event_loop(self) -> None:
        """Listen for AMI events"""
        while self.running and self.ami_socket:
            try:
                # Would need proper async socket handling here
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"AMI event loop error: {e}")
                break

    async def stop(self) -> None:
        """Stop the SIP bridge"""
        logger.info("Stopping SIP bridge...")
        self.running = False

        # Hangup all active calls
        for call_id in list(self.active_calls.keys()):
            self.active_calls[call_id] = CallState.HANGUP

        await self.disconnect_ami()
        logger.info("SIP bridge stopped")

    def get_status(self) -> dict:
        """Get current status"""
        return {
            "running": self.running,
            "active_calls": len(self.active_calls),
            "calls": {
                call_id: state.value
                for call_id, state in self.active_calls.items()
            }
        }


async def main():
    """Test the SIP bridge"""
    config = CallConfig(
        asterisk_host="localhost",
        asterisk_port=5038,
        sip_extension="6000"
    )

    bridge = SIPBridge(config)

    # Test AMI connection
    connected = await bridge.connect_ami()
    print(f"AMI connected: {connected}")

    if connected:
        await bridge.disconnect_ami()

    print(f"Bridge status: {bridge.get_status()}")


if __name__ == "__main__":
    asyncio.run(main())