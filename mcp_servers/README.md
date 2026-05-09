# MCP Servers for Dexter Voice Agent

## Overview
MCP (Model Context Protocol) servers expose tools to the voice agent.

## Servers

### SearXNG MCP
Web search via local SearXNG instance at localhost:8888.

### Filesystem MCP
Read/write files on clawbox, restricted to /home/tyler/.

### Shell MCP
Execute shell commands (restricted).

## Register with Claude Code
```bash
claude mcp add searxng /home/tyler/voice-agent/mcp_servers/searxng_mcp.py
claude mcp add filesystem /home/tyler/voice-agent/mcp_servers/filesystem_mcp.py
claude mcp add shell /home/tyler/voice-agent/mcp_servers/shell_mcp.py
```
