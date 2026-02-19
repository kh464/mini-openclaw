"""LLM reasoning node -- calls the model and returns response."""

from langchain_core.messages import AIMessage


async def reason_node(state: dict) -> dict:
    """Call LLM with current messages using streaming for real token-level events.

    When the engine uses astream_events(), the astream() call here
    emits on_chat_model_stream callbacks that the engine captures.
    Falls back to ainvoke() if streaming is unsupported by the provider.
    """
    llm = state["llm"]
    messages = state["messages"]
    tools = state.get("tools", [])

    llm_to_use = llm.bind_tools(tools) if tools else llm

    try:
        # Use astream for real token-level streaming
        response = None
        async for chunk in llm_to_use.astream(messages):
            if response is None:
                response = chunk
            else:
                response = response + chunk
    except Exception:
        # Fallback to non-streaming if provider doesn't support it
        response = await llm_to_use.ainvoke(messages)

    if response is None:
        response = await llm_to_use.ainvoke(messages)

    return {"messages": messages + [response], "last_response": response}
