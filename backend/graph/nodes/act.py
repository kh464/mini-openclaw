"""Tool execution node -- runs tool calls from the last AI message."""

from langchain_core.messages import ToolMessage


async def act_node(state: dict) -> dict:
    """Execute tool calls from last AI message and append results."""
    last = state["last_response"]
    tool_calls = last.tool_calls if hasattr(last, "tool_calls") else []
    tool_map = {t.name: t for t in state.get("tools", [])}
    messages = list(state["messages"])

    for tc in tool_calls:
        tool = tool_map.get(tc["name"])
        if tool:
            result = await tool.ainvoke(tc["args"])
        else:
            result = f"Error: unknown tool '{tc['name']}'"
        messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    return {"messages": messages, "iteration": state.get("iteration", 0) + 1}
