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
    try:
        async for event in agent_manager.astream(message, session_id):
            sse_data = json.dumps({"type": event.type, **event.data}, ensure_ascii=False)
            yield f"event: {event.type}\ndata: {sse_data}\n\n"

            if event.type == "done":
                full_content = event.data.get("content", "")

    except Exception as e:
        error_data = json.dumps({"type": "error", "error": str(e)}, ensure_ascii=False)
        yield f"event: error\ndata: {error_data}\n\n"

    # Save assistant response
    if full_content:
        agent_manager.session_manager.save_message(session_id, "assistant", full_content)
