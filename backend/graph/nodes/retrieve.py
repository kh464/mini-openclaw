"""RAG retrieval node -- runs hybrid search before LLM reasoning."""


async def retrieve_node(state: dict) -> dict:
    """Retrieve relevant memory/knowledge and inject into messages."""
    retriever = state.get("retriever")
    if not retriever:
        return state

    query = state["messages"][-1].content if state["messages"] else ""
    docs = await retriever.ainvoke(query)

    if docs:
        context_parts = [f"[{i+1}] {d.page_content[:500]}" for i, d in enumerate(docs[:3])]
        context_text = "\n---\n".join(context_parts)
        retrieval_msg = f"[Memory retrieval results]\n{context_text}"

        from langchain_core.messages import SystemMessage
        messages = list(state["messages"])
        messages.insert(-1, SystemMessage(content=retrieval_msg))
        return {
            **state,
            "messages": messages,
            "retrieval_results": [
                {"text": d.page_content, "score": d.metadata.get("score", 0)}
                for d in docs[:3]
            ],
        }
    return state
