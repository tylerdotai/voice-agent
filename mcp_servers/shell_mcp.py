"""Shell MCP Server for running commands."""
import subprocess

def run_command(cmd: str) -> str:
    """Execute a shell command."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return output[:2000]  # Limit output size
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print("Shell MCP Server")
    print(run_command("echo hello"))
