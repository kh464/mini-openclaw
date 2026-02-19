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

        final_content = ""
        for iteration in range(MAX_ITERATIONS):
            current_content = ""
            tool_calls: list[dict] = []

            try:
                async for evt_type, data in self._call_llm_streaming(messages):
                    if evt_type == "token":
                        yield AgentEvent(type="token", data={"content": data})
                        current_content += data
                    elif evt_type == "tool_calls":
                        tool_calls = data
            except Exception:
                # Fallback to non-streaming
                result = await self._call_llm(messages)
                current_content = result.get("content", "")
                if current_content:
                    yield AgentEvent(type="token", data={"content": current_content})
                tool_calls = result.get("tool_calls", [])

            final_content = current_content

            if not tool_calls:
                break

            # Process tool calls
            messages.append({
                "role": "assistant",
                "content": current_content or None,
                "tool_calls": tool_calls,
            })

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

        yield AgentEvent(type="done", data={"content": final_content})

    async def _call_llm_streaming(self, messages: list[dict]):
        """Streaming LLM call. Yields ("token", str) and ("tool_calls", list) tuples."""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if self.tools_schema:
            payload["tools"] = self.tools_schema

        tool_calls_acc: list[dict] = []

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", f"{self.api_base}/chat/completions",
                headers=headers, json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"]

                        # Text token
                        if delta.get("content"):
                            yield ("token", delta["content"])

                        # Tool call chunks (accumulate across stream)
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                while len(tool_calls_acc) <= idx:
                                    tool_calls_acc.append(
                                        {"id": "", "function": {"name": "", "arguments": ""}}
                                    )
                                if tc.get("id"):
                                    tool_calls_acc[idx]["id"] = tc["id"]
                                fn = tc.get("function", {})
                                if fn.get("name"):
                                    tool_calls_acc[idx]["function"]["name"] += fn["name"]
                                if fn.get("arguments"):
                                    tool_calls_acc[idx]["function"]["arguments"] += fn["arguments"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        # Yield accumulated tool calls after stream ends
        if tool_calls_acc:
            yield ("tool_calls", tool_calls_acc)

    async def _call_llm(self, messages: list[dict]) -> dict:
        """Non-streaming fallback for providers that don't support streaming."""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict = {
            "model": self.model,
            "messages": messages,
        }
        if self.tools_schema:
            payload["tools"] = self.tools_schema

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
