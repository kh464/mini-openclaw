"""Self-built agent loop -- no LangChain dependency. ~100 lines of core logic."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from graph.engines.base import BaseEngine, AgentEvent

MAX_ITERATIONS = 20


class RawLoopEngine(BaseEngine):
    def __init__(self, api_base: str, api_key: str, model: str, tools: list[dict],
                 tool_executor: dict):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.tools_schema = tools       # OpenAI-format tool schemas
        self.tool_executor = tool_executor  # name -> callable

    async def astream(
        self,
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> AsyncIterator[AgentEvent]:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        content = ""
        for iteration in range(MAX_ITERATIONS):
            response = await self._call_llm(messages)

            # Yield text tokens
            content = response.get("content", "")
            if content:
                yield AgentEvent(type="token", data={"content": content})

            # Check for tool calls
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                break

            # Process each tool call
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])

                yield AgentEvent(type="tool_start", data={"tool": fn_name, "input": fn_args})

                executor = self.tool_executor.get(fn_name)
                if executor:
                    result = await executor(fn_args) if callable(executor) else str(executor)
                else:
                    result = f"Error: unknown tool '{fn_name}'"

                yield AgentEvent(type="tool_end", data={"tool": fn_name, "output": str(result)})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result),
                })

            yield AgentEvent(type="new_response", data={})

        yield AgentEvent(type="done", data={"content": content})

    async def _call_llm(self, messages: list[dict]) -> dict:
        """Call OpenAI-compatible chat completion API (non-streaming for simplicity)."""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": self.tools_schema if self.tools_schema else None,
        }
        if not payload["tools"]:
            del payload["tools"]

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]
        return {
            "content": choice.get("content", ""),
            "tool_calls": choice.get("tool_calls", []),
        }
