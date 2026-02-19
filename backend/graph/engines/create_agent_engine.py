"""LangGraph prebuilt create_react_agent wrapper engine -- production mode."""

from __future__ import annotations

from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from graph.engines.base import AgentEvent, BaseEngine


class CreateAgentEngine(BaseEngine):
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    async def astream(
        self,
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> AsyncIterator[AgentEvent]:
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt,
        )

        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=message))

        final_content = ""
        async for event in agent.astream({"messages": messages}):
            # Normalize LangGraph events to our AgentEvent format
            if isinstance(event, dict):
                for key, value in event.items():
                    if key == "agent":
                        msgs = value.get("messages", [])
                        for m in msgs:
                            if hasattr(m, "content") and m.content:
                                yield AgentEvent(
                                    type="token",
                                    data={"content": m.content},
                                )
                                final_content = m.content
                            if hasattr(m, "tool_calls") and m.tool_calls:
                                for tc in m.tool_calls:
                                    yield AgentEvent(
                                        type="tool_start",
                                        data={
                                            "tool": tc["name"],
                                            "input": tc.get("args", {}),
                                        },
                                    )
                    elif key == "tools":
                        msgs = value.get("messages", [])
                        for m in msgs:
                            yield AgentEvent(
                                type="tool_end",
                                data={
                                    "tool": getattr(m, "name", "tool"),
                                    "output": getattr(m, "content", ""),
                                },
                            )
                        yield AgentEvent(type="new_response", data={})

        yield AgentEvent(type="done", data={"content": final_content})
