# backend/api/tokens.py
"""Token counting endpoints."""

import tiktoken
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/tokens", tags=["tokens"])

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


@router.get("/session/{session_id}")
async def session_tokens(session_id: str, request: Request):
    """Get token breakdown for a session."""
    am = request.app.state.agent_manager

    # System prompt tokens
    system_prompt = am.prompt_builder.build(rag_mode=am.config.rag_mode)
    system_tokens = count_tokens(system_prompt)

    # History tokens
    messages = am.session_manager.load_session(session_id)
    history_tokens = sum(count_tokens(m.get("content", "")) for m in messages)

    # Compressed context tokens
    compressed = am.session_manager.get_compressed_context(session_id)
    compressed_tokens = count_tokens(compressed) if compressed else 0

    return {
        "session_id": session_id,
        "system_prompt_tokens": system_tokens,
        "history_tokens": history_tokens,
        "compressed_context_tokens": compressed_tokens,
        "total_tokens": system_tokens + history_tokens + compressed_tokens,
        "message_count": len(messages),
    }


class FileTokenRequest(BaseModel):
    paths: list[str]


@router.post("/files")
async def file_tokens(req: FileTokenRequest, request: Request):
    """Count tokens for specified files."""
    base_dir = request.app.state.base_dir
    results = {}
    for path in req.paths:
        target = (base_dir / path).resolve()
        # Prevent path traversal
        if not str(target).startswith(str(base_dir)):
            results[path] = -1
            continue
        if target.is_file():
            try:
                content = target.read_text(encoding="utf-8")
                results[path] = count_tokens(content)
            except Exception:
                results[path] = -1
        else:
            results[path] = -1
    return {"tokens": results, "total": sum(v for v in results.values() if v >= 0)}
