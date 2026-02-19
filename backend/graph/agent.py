# backend/graph/agent.py
"""AgentManager — unified entry point that switches between engines."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator

from config import AppConfig, load_config
from graph.engines.base import BaseEngine, AgentEvent
from graph.prompt_builder import PromptBuilder
from graph.session_manager import SessionManager
from providers.registry import get_llm, get_embeddings
from tools import get_all_tools
from tools.skills_scanner import write_snapshot


class AgentManager:
    def __init__(self, base_dir: str | Path, config: AppConfig | None = None):
        self.base_dir = Path(base_dir).resolve()
        self.config = config or load_config()
        self.llm = None
        self.tools = []
        self.session_manager = SessionManager(self.base_dir / "sessions")
        self.prompt_builder = PromptBuilder(self.base_dir)

    def initialize(self):
        """Called at startup — build LLM, tools, scan skills."""
        write_snapshot(self.base_dir)
        self.llm = get_llm(self.config)
        self.tools = get_all_tools(self.base_dir)

    def _get_engine(self) -> BaseEngine:
        engine_name = self.config.agent_engine

        if engine_name == "langgraph":
            from graph.engines.langgraph_engine import LangGraphEngine
            return LangGraphEngine(
                llm=self.llm,
                tools=self.tools,
                memory_dir=str(self.base_dir / "memory"),
            )
        elif engine_name == "create_agent":
            from graph.engines.create_agent_engine import CreateAgentEngine
            return CreateAgentEngine(llm=self.llm, tools=self.tools)
        elif engine_name == "raw_loop":
            from graph.engines.raw_loop_engine import RawLoopEngine
            # Build OpenAI-format tool schemas from LangChain tools
            tool_schemas = [_lc_tool_to_openai_schema(t) for t in self.tools]
            tool_executor = {t.name: t.ainvoke for t in self.tools}
            return RawLoopEngine(
                api_base=self._get_api_base(),
                api_key=self._get_api_key(),
                model=self.config.llm.model,
                tools=tool_schemas,
                tool_executor=tool_executor,
            )
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

    async def astream(self, message: str, session_id: str) -> AsyncIterator[AgentEvent]:
        history = self.session_manager.load_session_for_agent(session_id)
        system_prompt = self.prompt_builder.build(rag_mode=self.config.rag_mode)
        engine = self._get_engine()

        async for event in engine.astream(message, history, system_prompt):
            yield event

    def _get_api_base(self) -> str:
        from providers.registry import get_provider_spec
        spec = get_provider_spec(self.config.llm.provider)
        creds = self.config.providers.get(self.config.llm.provider)
        return (creds.api_base if creds and creds.api_base else "") or (spec.api_base_default if spec else "")

    def _get_api_key(self) -> str:
        import os
        from providers.registry import get_provider_spec
        spec = get_provider_spec(self.config.llm.provider)
        if spec and spec.env_key:
            return os.getenv(spec.env_key, "")
        return ""


def _lc_tool_to_openai_schema(tool) -> dict:
    """Convert LangChain tool to OpenAI function-calling schema."""
    schema = tool.args_schema.schema() if hasattr(tool, "args_schema") and tool.args_schema else {}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }
