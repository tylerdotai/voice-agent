# Voice Agent Dockerfile
# Multi-stage build for production deployment

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.12-slim as runtime

LABEL maintainer="voice-agent"
LABEL description="Local voice AI agent with VAD, STT, LLM, and TTS"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONBLABLA=1 \
    OLLAMA_HOST=127.0.0.1:11434 \
    VOICE_AGENT_HOME=/app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    sox \
    libasound2-dev \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r voiceagent && useradd -r -g voiceagent voiceagent

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Copy application files
COPY --chown=voiceagent:voiceagent . .

# Create necessary directories
RUN mkdir -p /app/logs /app/models && chown -R voiceagent:voiceagent /app

# Switch to non-root user
USER voiceagent

# Expose ports
EXPOSE 11434 7880 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:11434/api/tags || exit 1

# Default command - start Ollama server in background, then voice agent
CMD ["sh", "-c", "ollama serve & sleep 3 && python baseline_loop.py"]

# For development/testing, mount volumes:
# -v $(pwd)/logs:/app/logs
# -v ~/.ollama:/root/.ollama