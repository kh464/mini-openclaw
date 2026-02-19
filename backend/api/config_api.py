# backend/api/config_api.py
"""Configuration APIs -- RAG mode, engine, memory backend switching."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import save_config

router = APIRouter(prefix="/api/config", tags=["config"])


class EngineUpdate(BaseModel):
    engine: str  # "create_agent" | "langgraph" | "raw_loop"


class MemoryBackendUpdate(BaseModel):
    backend: str  # "native" | "mem0"


class RagModeUpdate(BaseModel):
    enabled: bool


# Engine endpoints
@router.get("/engine")
async def get_engine(request: Request):
    cfg = request.app.state.agent_manager.config
    return {"engine": cfg.agent_engine}


@router.put("/engine")
async def set_engine(req: EngineUpdate, request: Request):
    am = request.app.state.agent_manager
    if req.engine not in ("create_agent", "langgraph", "raw_loop"):
        raise HTTPException(status_code=400, detail=f"Invalid engine: {req.engine}")
    am.config.agent_engine = req.engine
    save_config(am.config)
    return {"engine": am.config.agent_engine}


# Memory backend endpoints
@router.get("/memory-backend")
async def get_memory_backend(request: Request):
    cfg = request.app.state.agent_manager.config
    return {"backend": cfg.memory_backend}


@router.put("/memory-backend")
async def set_memory_backend(req: MemoryBackendUpdate, request: Request):
    am = request.app.state.agent_manager
    if req.backend not in ("native", "mem0"):
        raise HTTPException(status_code=400, detail=f"Invalid backend: {req.backend}")
    am.config.memory_backend = req.backend
    save_config(am.config)
    return {"backend": am.config.memory_backend}


# RAG mode endpoints
@router.get("/rag-mode")
async def get_rag_mode(request: Request):
    cfg = request.app.state.agent_manager.config
    return {"enabled": cfg.rag_mode}


@router.put("/rag-mode")
async def set_rag_mode(req: RagModeUpdate, request: Request):
    am = request.app.state.agent_manager
    am.config.rag_mode = req.enabled
    save_config(am.config)
    return {"enabled": am.config.rag_mode}


# Memory flush endpoint
@router.post("/memory/flush")
async def flush_memory(request: Request):
    """Manually trigger memory flush (Daily Logs -> MEMORY.md)."""
    from pathlib import Path
    from memory.native.daily_log import DailyLog
    from memory.native.knowledge import KnowledgeStore
    from memory.native.flush import flush_memories

    am = request.app.state.agent_manager
    if not am.llm:
        raise HTTPException(status_code=503, detail="LLM not initialized")

    base_dir: Path = request.app.state.base_dir
    daily_log = DailyLog(base_dir / "memory" / "logs")
    knowledge = KnowledgeStore(base_dir / "memory" / "MEMORY.md")

    result = await flush_memories(am.llm, daily_log, knowledge)
    return {"status": "flushed", "content": result}


# Daily logs listing
@router.get("/memory/daily-logs")
async def list_daily_logs(request: Request):
    """List available daily log files."""
    from memory.native.daily_log import DailyLog

    base_dir = request.app.state.base_dir
    dl = DailyLog(base_dir / "memory" / "logs")
    return {"logs": dl.list_logs()}
