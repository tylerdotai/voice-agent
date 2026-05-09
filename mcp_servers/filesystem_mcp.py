"""Filesystem MCP Server for reading/writing files."""
import os
from pathlib import Path

BASE_DIR = Path("/home/tyler")

def read_file(path: str) -> str:
    """Read a file from disk."""
    try:
        full_path = BASE_DIR / path
        return full_path.read_text()
    except Exception as e:
        return f"Error: {e}"

def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        full_path = BASE_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return f"Written to {path}"
    except Exception as e:
        return f"Error: {e}"

def list_directory(path: str = ".") -> list:
    """List directory contents."""
    try:
        full_path = BASE_DIR / path
        return [str(p.name) for p in full_path.iterdir()]
    except Exception as e:
        return [f"Error: {e}"]

if __name__ == "__main__":
    print("Filesystem MCP Server")
    print(list_directory("."))
