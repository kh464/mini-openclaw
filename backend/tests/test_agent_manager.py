# backend/tests/test_agent_manager.py
import tempfile
from pathlib import Path


def test_agent_manager_init():
    from graph.agent import AgentManager
    from config import AppConfig
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        # Create minimal workspace
        for d in ["workspace", "memory", "memory/logs", "skills", "sessions", "knowledge", "storage"]:
            (base / d).mkdir(parents=True, exist_ok=True)
        (base / "workspace" / "SOUL.md").write_text("soul")
        (base / "workspace" / "IDENTITY.md").write_text("id")
        (base / "workspace" / "USER.md").write_text("user")
        (base / "workspace" / "AGENTS.md").write_text("agents")
        (base / "memory" / "MEMORY.md").write_text("mem")

        cfg = AppConfig()
        am = AgentManager(base_dir=td, config=cfg)
        assert am.session_manager is not None
        assert am.config.agent_engine == "langgraph"


def test_agent_manager_get_engine_langgraph():
    from graph.agent import AgentManager
    from graph.engines.langgraph_engine import LangGraphEngine
    from config import AppConfig
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for d in ["workspace", "memory", "memory/logs", "skills", "sessions", "knowledge", "storage"]:
            (base / d).mkdir(parents=True, exist_ok=True)
        (base / "workspace" / "SOUL.md").write_text("soul")
        (base / "workspace" / "IDENTITY.md").write_text("id")
        (base / "workspace" / "USER.md").write_text("user")
        (base / "workspace" / "AGENTS.md").write_text("agents")
        (base / "memory" / "MEMORY.md").write_text("mem")

        cfg = AppConfig(agent_engine="langgraph")
        am = AgentManager(base_dir=td, config=cfg)
        # Need a mock LLM to get engine
        class MockLLM:
            pass
        am.llm = MockLLM()
        am.tools = []
        engine = am._get_engine()
        assert isinstance(engine, LangGraphEngine)


def test_lc_tool_to_openai_schema():
    from graph.agent import _lc_tool_to_openai_schema
    from langchain_core.tools import tool as lc_tool

    @lc_tool
    def test_tool(query: str) -> str:
        """A test tool."""
        return query

    schema = _lc_tool_to_openai_schema(test_tool)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "test_tool"
    assert "query" in str(schema["function"]["parameters"])
