"""LangGraph prebuilt create_react_agent wrapper engine -- production mode."""

from __future__ import annotations

from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from graph.engines.base import AgentEvent, BaseEngine


class CreateAgentEngine(BaseEngine):
    def __init__(self, llm, tools):
        # 初始化引擎，注入大语言模型实例和可用的工具列表
        self.llm = llm
        self.tools = tools

    async def astream(
        self,
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> AsyncIterator[AgentEvent]:
        # 使用 LangGraph 预构建函数创建一个 ReAct 智能体
        # 它会自动处理“思考-行动-观察”循环
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt,
        )
        # 消息格式转换：将字典格式的历史记录转换为 LangChain 的消息对象
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        # 添加当前用户发送的新消息
        messages.append(HumanMessage(content=message))

        try:
            # 优先尝试使用“事件流”模式，它可以提供更细粒度的 Token 级输出
            async for event in self._stream_with_events(agent, messages):
                yield event
        except Exception:
            # Fallback to node-level streaming
            # 如果事件流模式失败（某些模型或环境不支持），回退到“节点更新”流模式
            async for event in self._stream_with_updates(agent, messages):
                yield event

    async def _stream_with_events(
        self, agent, messages: list
    ) -> AsyncIterator[AgentEvent]:
        """Real token-level streaming via astream_events."""
        current_parts: list[str] = []  # 用于暂存当前轮次的 Token 片段
        final_content = ""            # 最终拼接的完整回答内容
        had_tool_execution = False    # 状态位：标记上一轮是否刚执行完工具
        # 使用 v2 版本的 astream_events 监听智能体内部发生的一切
        async for event in agent.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]  # 获取事件类型
            # 场景 A：模型正在输出文本流
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content = getattr(chunk, "content", "")
                if isinstance(content, str) and content:
                    # 如果刚才执行了工具，现在模型开始根据工具结果说话
                    # 发送 new_response 事件让前端知道这是一个“新段落”
                    if had_tool_execution:
                        yield AgentEvent(type="new_response", data={})
                        had_tool_execution = False
                    yield AgentEvent(type="token", data={"content": content})
                    current_parts.append(content)
            # 场景 B：模型这一轮回答结束了（可能是文本结束，也可能是准备调用工具）
            elif kind == "on_chat_model_end":
                output = event["data"]["output"]
                # Fallback for non-streaming providers
                # 针对不支持流式输出的模型的兜底逻辑：一次性获取所有内容
                if not current_parts:
                    content = getattr(output, "content", "")
                    if content:
                        if had_tool_execution:
                            yield AgentEvent(type="new_response", data={})
                            had_tool_execution = False
                        yield AgentEvent(type="token", data={"content": content})
                        current_parts.append(content)
                # 记录本轮结束时的完整文本
                final_content = "".join(current_parts)
                current_parts.clear()
                # 核心逻辑：检查模型是否发起了工具调用请求
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
            # 场景 C：工具执行完毕（例如终端命令运行结束）
            elif kind == "on_tool_end":
                tool_name = event.get("name", "tool")
                output = event["data"].get("output", "")
                # 产生 tool_end 事件，UI 会显示工具执行的结果
                yield AgentEvent(
                    type="tool_end",
                    data={"tool": tool_name, "output": str(output)},
                )
                # 标记已执行工具，下一轮模型回复需要触发“新响应”信号
                had_tool_execution = True

        yield AgentEvent(type="done", data={"content": final_content})

    async def _stream_with_updates(
        self, agent, messages: list
    ) -> AsyncIterator[AgentEvent]:
        """Fallback: node-level streaming."""
        final_content = ""
        # astream 会产出每个节点执行完后的状态快照，包含模型、工具等节点的状态
        async for event in agent.astream({"messages": messages}):
            if isinstance(event, dict):
                for key, value in event.items():
                    # 如果是 'agent' 节点产生的信息（包含模型回答或工具调用指令）
                    if key == "agent":
                        msgs = value.get("messages", [])
                        for m in msgs:
                            # 提取文本内容
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
                            # 通知前端准备接收工具执行后的模型新回复
                        yield AgentEvent(type="new_response", data={})

        yield AgentEvent(type="done", data={"content": final_content})
"""ReAct 循环：通过 create_react_agent 自动管理“思考（模型）-执行（工具）-反馈（模型）”的循环逻辑。

状态机感知：代码通过 had_tool_execution 状态位巧妙地处理了 UI 上的视觉分隔。当模型在工具执行后重新开始说话时，发送 new_response 信号。

标准化输出：无论底层事件如何复杂，最终都通过 AgentEvent 统一输出，使得前端（如 ThoughtChain.tsx 或 ChatMessage.tsx）能以统一的方式处理推理链和结果。"""