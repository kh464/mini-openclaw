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

        try:
            async for event in self._stream_with_events(agent, messages):
                yield event
        except Exception:
            # Fallback to node-level streaming
            async for event in self._stream_with_updates(agent, messages):
                yield event

    async def _stream_with_events(
        self, agent, messages: list
    ) -> AsyncIterator[AgentEvent]:
        """Real token-level streaming via astream_events."""
        current_parts: list[str] = []
        final_content = ""
        had_tool_execution = False

        async for event in agent.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content = getattr(chunk, "content", "")
                if isinstance(content, str) and content:
                    if had_tool_execution:
                        yield AgentEvent(type="new_response", data={})
                        had_tool_execution = False
                    yield AgentEvent(type="token", data={"content": content})
                    current_parts.append(content)

            elif kind == "on_chat_model_end":
                output = event["data"]["output"]
                # Fallback for non-streaming providers
                if not current_parts:
                    content = getattr(output, "content", "")
                    if content:
                        if had_tool_execution:
                            yield AgentEvent(type="new_response", data={})
                            had_tool_execution = False
                        yield AgentEvent(type="token", data={"content": content})
                        current_parts.append(content)

                final_content = "".join(current_parts)
                current_parts.clear()

                # Tool calls
                if hasattr(output, "tool_calls") and output.tool_calls:
                    for tc in output.tool_calls:
                        yield AgentEvent(
                            type="tool_start",
                            data={
                                "tool": tc["name"],
                                "input": tc.get("args", {}),
                            },
                        )

            elif kind == "on_tool_end":
                tool_name = event.get("name", "tool")
                output = event["data"].get("output", "")
                yield AgentEvent(
                    type="tool_end",
                    data={"tool": tool_name, "output": str(output)},
                )
                had_tool_execution = True

        yield AgentEvent(type="done", data={"content": final_content})

    async def _stream_with_updates(
        self, agent, messages: list
    ) -> AsyncIterator[AgentEvent]:
        """Fallback: node-level streaming."""
        final_content = ""
        async for event in agent.astream({"messages": messages}):
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
