# Deployment Guide

## Systemd Service

```bash
# Install
systemctl --user daemon-reload
systemctl --user enable voice-agent

# Start
systemctl --user start voice-agent

# Check status
systemctl --user status voice-agent

# View logs
journalctl --user -u voice-agent -f
```

## Environment Variables

- `OLLAMA_URL` - Ollama endpoint (default: http://localhost:11434)
- `MINIMAX_API_KEY` - MiniMax API key for complex reasoning

## Ports

- 7880: LiveKit server (WebSocket)
- 8888: SearXNG (web search)
- 11434: Ollama

## Tailscale

For remote access, connect via Tailscale. The agent runs on clawbox at 100.79.252.47.
