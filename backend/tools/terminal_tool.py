"""Sandboxed terminal tool — allowlist-based command filtering.

SECURITY NOTE: This tool runs commands via subprocess. The allowlist approach
is safer than a blocklist but not bulletproof. For production deployments,
run commands in a Docker container or chroot jail.
"""

import shlex
import subprocess
from pathlib import Path

from langchain_core.tools import tool as lc_tool, BaseTool

# Only these command prefixes are allowed
ALLOWED_COMMANDS = {
    "ls", "dir", "cat", "head", "tail", "echo", "pwd", "whoami",
    "python", "python3", "pip", "pip3", "node", "npm", "npx",
    "git", "grep", "find", "wc", "sort", "uniq", "diff", "curl", "wget",
    "cd", "mkdir", "cp", "mv", "touch", "which", "where", "env",
    "type", "tree", "date", "uname",
}
MAX_OUTPUT = 5000
TIMEOUT = 30


def _get_base_command(command: str) -> str:
    """Extract the base command name from a command string."""
    try:
        parts = shlex.split(command.strip())
        if parts:
            # Handle paths like /usr/bin/python -> python
            return Path(parts[0]).name.lower()
    except ValueError:
        pass
    # Fallback: first whitespace-delimited token
    first = command.strip().split()[0] if command.strip() else ""
    return Path(first).name.lower()


def create_terminal_tool(root_dir: str) -> BaseTool:
    root = Path(root_dir).resolve()

    @lc_tool
    def terminal(command: str) -> str:
        """Execute a shell command in a sandboxed environment. Use for system operations."""
        base_cmd = _get_base_command(command)
        if base_cmd not in ALLOWED_COMMANDS:
            return f"Blocked: command '{base_cmd}' is not in the allowed list. Allowed: {', '.join(sorted(ALLOWED_COMMANDS))}"
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=TIMEOUT, cwd=str(root),
            )
            output = (result.stdout + result.stderr).strip()
            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + "\n...[truncated]"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "Blocked: command timed out (30s limit)."
        except Exception as e:
            return f"Error: {e}"

    return terminal
