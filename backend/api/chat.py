# backend/api/chat.py
"""POST /api/chat — SSE streaming chat endpoint."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str
    stream: bool = True


@router.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    agent_manager = request.app.state.agent_manager

    if not agent_manager.llm:
        raise HTTPException(status_code=503, detail="Agent not initialized. Configure LLM provider in .env")

    # Save user message
    agent_manager.session_manager.save_message(req.session_id, "user", req.message)

    if req.stream:
        return StreamingResponse(
            _stream_response(agent_manager, req.message, req.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-streaming: collect all events
        full_content = ""
        async for event in agent_manager.astream(req.message, req.session_id):
            if event.type == "done":
                full_content = event.data.get("content", "")

        agent_manager.session_manager.save_message(req.session_id, "assistant", full_content)
        return {"content": full_content, "session_id": req.session_id}


async def _stream_response(agent_manager, message: str, session_id: str):
    """Generate SSE events from agent stream."""
    full_content = ""
    thought_chain: list[dict] = []
    try:
        async for event in agent_manager.astream(message, session_id):
            sse_data = json.dumps({"type": event.type, **event.data}, ensure_ascii=False)
            yield f"event: {event.type}\ndata: {sse_data}\n\n"

            if event.type == "done":
                full_content = event.data.get("content", "")
            elif event.type in ("tool_start", "tool_end", "retrieval"):
                thought_chain.append({"type": event.type, **event.data})

    except Exception as e:
        error_data = json.dumps({"type": "error", "error": str(e)}, ensure_ascii=False)
        yield f"event: error\ndata: {error_data}\n\n"

    # Save assistant response with thought chain
    if full_content:
        agent_manager.session_manager.save_message(
            session_id, "assistant", full_content,
            thought_chain=thought_chain or None,
        )

    # Auto-generate title on first exchange (2 messages = 1 user + 1 assistant)
    try:
        msgs = agent_manager.session_manager.load_session(session_id)
        if len(msgs) == 2 and agent_manager.llm:
            title = await _generate_title(agent_manager.llm, msgs)
            agent_manager.session_manager.rename_session(session_id, title)
            title_data = json.dumps(
                {"type": "title_generated", "title": title, "session_id": session_id},
                ensure_ascii=False,
            )
            yield f"event: title_generated\ndata: {title_data}\n\n"
    except Exception:
        pass  # Non-critical — don't fail the response


async def _generate_title(llm, messages: list[dict]) -> str:
    """Generate a short conversation title from the first exchange."""
    conversation = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in messages[:4])
    prompt = (
        "Given this conversation, generate a very short title "
        "(5-10 words, in the language of the conversation). "
        "Output ONLY the title, nothing else:\n\n"
        f"{conversation}\n\nTitle:"
    )
    response = await llm.ainvoke(prompt)
    title = response.content.strip().strip('"').strip("'")[:50]
    return title or "New Chat"
