# backend/tests/test_tools_basic.py
import tempfile
from pathlib import Path

import pytest


def test_terminal_echo():
    from tools.terminal_tool import create_terminal_tool
    with tempfile.TemporaryDirectory() as td:
        tool = create_terminal_tool(root_dir=td)
        result = tool.invoke({"command": "echo hello"})
        assert "hello" in result


def test_terminal_blocks_dangerous():
    from tools.terminal_tool import create_terminal_tool
    with tempfile.TemporaryDirectory() as td:
        tool = create_terminal_tool(root_dir=td)
        result = tool.invoke({"command": "rm -rf /"})
        assert "blocked" in result.lower() or "not in the allowed" in result.lower()


def test_read_file():
    from tools.read_file_tool import create_read_file_tool
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "test.txt").write_text("hello world")
        tool = create_read_file_tool(root_dir=td)
        result = tool.invoke({"path": "test.txt"})
        assert "hello world" in result


def test_read_file_blocks_traversal():
    from tools.read_file_tool import create_read_file_tool
    with tempfile.TemporaryDirectory() as td:
        tool = create_read_file_tool(root_dir=td)
        result = tool.invoke({"path": "../../etc/passwd"})
        assert "denied" in result.lower() or "error" in result.lower()


def test_python_repl():
    from tools.python_repl_tool import create_python_repl_tool
    tool = create_python_repl_tool()
    result = tool.invoke({"code": "print(2 + 3)"})
    assert "5" in result
