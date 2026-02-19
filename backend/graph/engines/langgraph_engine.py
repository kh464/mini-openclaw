"""LangGraph StateGraph agent engine -- the teaching core."""

from __future__ import annotations

from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import START, END, StateGraph
from typing_extensions import TypedDict

from graph.engines.base import BaseEngine, AgentEvent
from graph.nodes.reason import reason_node
from graph.nodes.act import act_node
from graph.nodes.retrieve import retrieve_node
from graph.nodes.reflect import reflect_node
from graph.nodes.memory_flush import memory_flush_node

MAX_ITERATIONS = 20


class AgentState(TypedDict):
    messages: list
    llm: Any
    tools: list
    retriever: Any
    memory_dir: str
    last_response: Any
    reflection: str
    retrieval_results: list
    flushed_memories: list
    iteration: int


def should_continue(state: AgentState) -> str:
    """Route: if last response has tool_calls -> 'act', else -> 'reflect'."""
    last = state.get("last_response")
    if last and hasattr(last, "tool_calls") and last.tool_calls:
        if state.get("iteration", 0) < MAX_ITERATIONS:
            return "act"
    return "reflect"


class LangGraphEngine(BaseEngine):
    def __init__(self, llm, tools, retriever=None, memory_dir: str = ""):
        self.llm = llm
        self.tools = tools
        self.retriever = retriever
        self.memory_dir = memory_dir
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("retrieve", retrieve_node)
        builder.add_node("reason", reason_node)
        builder.add_node("act", act_node)
        builder.add_node("reflect", reflect_node)
        builder.add_node("memory_flush", memory_flush_node)

        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "reason")
        builder.add_conditional_edges(
            "reason", should_continue, {"act": "act", "reflect": "reflect"}
        )
        builder.add_edge("act", "reason")
        builder.add_edge("reflect", "memory_flush")
        builder.add_edge("memory_flush", END)

        return builder.compile()

    async def astream(
        self,
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> AsyncIterator[AgentEvent]:
        # Convert history dicts to LangChain messages
        messages = [SystemMessage(content=system_prompt)]
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=message))

        initial_state: AgentState = {
            "messages": messages,
            "llm": self.llm,
            "tools": self.tools,
            "retriever": self.retriever,
            "memory_dir": self.memory_dir,
            "last_response": None,
            "reflection": "",
            "retrieval_results": [],
            "flushed_memories": [],
            "iteration": 0,
        }

        try:
            async for event in self._stream_with_events(initial_state):
                yield event
        except Exception:
            # Fallback to node-level streaming if astream_events fails
            async for event in self._stream_with_updates(initial_state):
                yield event

    # Nodes whose LLM calls should NOT be streamed to the user
    _INTERNAL_NODES = frozenset({"reflect", "memory_flush"})

    async def _stream_with_events(
        self, initial_state: AgentState
    ) -> AsyncIterator[AgentEvent]:
        """Real token-level streaming via astream_events."""
        current_parts: list[str] = []
        final_content = ""
        had_tool_execution = False
        done_sent = False

        async for event in self.graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            # Skip LLM events from internal nodes (reflect, memory_flush)
            node = event.get("metadata", {}).get("langgraph_node", "")

            # Emit done early when internal nodes start — user-facing content is complete
            if node in self._INTERNAL_NODES and not done_sent:
                yield AgentEvent(type="done", data={"content": final_content})
                done_sent = True
                continue

            if done_sent:
                continue  # Skip all remaining events from internal nodes

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
                # Fallback: if no streaming tokens were captured, yield full content
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

                # Check for tool calls
                if hasattr(output, "tool_calls") and output.tool_calls:
                    for tc in output.tool_calls:
                        yield AgentEvent(
                            type="tool_start",
                            data={"tool": tc["name"], "input": tc.get("args", {})},
                        )

            elif kind == "on_tool_end":
                tool_name = event.get("name", "tool")
                output = event["data"].get("output", "")
                yield AgentEvent(
                    type="tool_end",
                    data={"tool": tool_name, "output": str(output)},
                )
                had_tool_execution = True

            elif kind == "on_retriever_end":
                docs = event["data"].get("output", [])
                if docs:
                    yield AgentEvent(
                        type="retrieval",
                        data={
                            "results": [
                                {"text": d.page_content, "score": d.metadata.get("score", 0)}
                                for d in docs[:3]
                            ]
                        },
                    )

        if not done_sent:
            yield AgentEvent(type="done", data={"content": final_content})

    async def _stream_with_updates(
        self, initial_state: AgentState
    ) -> AsyncIterator[AgentEvent]:
        """Fallback: node-level streaming (no token-by-token, but still functional)."""
        final_content = ""
        seen_tool_msg_ids: set[str] = set()
        done_sent = False
        async for event in self.graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                # Emit done early when internal nodes start
                if node_name in self._INTERNAL_NODES and not done_sent:
                    yield AgentEvent(type="done", data={"content": final_content})
                    done_sent = True
                    continue

                if done_sent:
                    continue

                if node_name == "retrieve" and node_output.get("retrieval_results"):
                    yield AgentEvent(
                        type="retrieval",
                        data={"results": node_output["retrieval_results"]},
                    )

                if node_name == "reason":
                    last = node_output.get("last_response")
                    if last:
                        content = last.content if hasattr(last, "content") else ""
                        if content:
                            yield AgentEvent(
                                type="token", data={"content": content}
                            )
                            final_content = content
                        if hasattr(last, "tool_calls") and last.tool_calls:
                            for tc in last.tool_calls:
                                yield AgentEvent(
                                    type="tool_start",
                                    data={"tool": tc["name"], "input": tc["args"]},
                                )

                if node_name == "act":
                    msgs = node_output.get("messages", [])
                    for m in msgs:
                        if isinstance(m, ToolMessage):
                            msg_id = getattr(m, "tool_call_id", id(m))
                            if msg_id not in seen_tool_msg_ids:
                                seen_tool_msg_ids.add(msg_id)
                                yield AgentEvent(
                                    type="tool_end",
                                    data={"tool": getattr(m, "name", "tool"), "output": m.content},
                                )
                    yield AgentEvent(type="new_response", data={})

        if not done_sent:
            yield AgentEvent(type="done", data={"content": final_content})
