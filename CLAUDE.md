# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mini-OpenClaw** is a full-stack AI Agent teaching/research project. Backend is FastAPI + LangGraph, frontend is Next.js 14 + Tailwind. Python 3.12+, Node.js 18+.

## Common Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8002
pytest tests/ -v                    # 65 tests
pytest tests/test_api_chat.py -v    # Single file
```

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run build      # Production build
```

## Architecture

Three interchangeable agent engines, all sharing the same tools, memory, and session system:

1. **LangGraph Engine** (`graph/engines/langgraph_engine.py`) — 5-node StateGraph: retrieve → reason → act → reflect → memory_flush. Uses `astream_events(version="v2")` for real token streaming, with `_stream_with_updates` fallback.

2. **CreateAgent Engine** (`graph/engines/create_agent_engine.py`) — LangGraph prebuilt `create_react_agent`. Same `astream_events` streaming.

3. **RawLoop Engine** (`graph/engines/raw_loop_engine.py`) — ~100-line while-loop with streaming HTTP SSE parsing, no LangChain dependency.

### Key Entry Points

- `backend/app.py` — FastAPI app with lifespan, `load_dotenv()` before config imports
- `backend/graph/agent.py` — `AgentManager` dispatches to engines, builds tools
- `backend/providers/registry.py` — `get_llm()` / `get_embeddings()`, provider-specific handling via `ProviderSpec.manages_own_base` and `api_key_alias`
- `backend/api/chat.py` — SSE streaming endpoint with auto title generation
- `frontend/src/lib/store.tsx` — Global state with useReducer, SSE event handling

### Provider Specifics

- **ChatZhipuAI**: Uses `zhipuai_api_key` (not `api_key`), manages its own API endpoint (don't pass `base_url`). Set via `ProviderSpec(manages_own_base=True, api_key_alias="zhipuai_api_key")`.
- **OpenAI-compatible** (DeepSeek, OpenRouter, SiliconFlow): Use `ChatOpenAI` with `base_url`.

### Streaming Architecture

All engines emit `AgentEvent` objects (type: token/tool_start/tool_end/new_response/retrieval/done). The LangGraph engine filters out `reflect` and `memory_flush` node LLM events via `_INTERNAL_NODES` to prevent memory extraction JSON from leaking into the response.

### Security

- Python REPL: `SAFE_BUILTINS` allowlist, eval-first then exec fallback
- Terminal: `ALLOWED_COMMANDS` allowlist
- Session IDs: regex-validated `^[a-f0-9]{12}$`
- Token file paths: `.resolve()` + `startswith()` traversal prevention

## Directory Layout

- `backend/sessions/` and `backend/memory/` are runtime data (gitignored)
- `backend/config.json` is auto-generated from defaults (gitignored)
- `docs/` and `nanobot/` are pre-development reference materials
