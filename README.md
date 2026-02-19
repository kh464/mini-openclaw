# Mini-OpenClaw

> A hands-on AI Agent teaching and research project — build a phenomenal agent from scratch by studying the OpenClaw architecture.

## What Is This

Mini-OpenClaw is a full-stack AI Agent system built for **learning and experimentation**. It implements 3 progressively complex agent engines, a multi-layer memory system, and a modern chat UI — all in readable, educational code.

The project was designed by studying [OpenClaw](https://github.com/openclaw/openclaw) and [nanobot](https://github.com/HKUDS/nanobot), extracting core concepts and re-implementing them from scratch.

## Architecture

```
Frontend (Next.js)  ←→  Backend (FastAPI)
                          ├── 3 Agent Engines (LangGraph / create_react_agent / Raw Loop)
                          ├── 5-Node StateGraph (retrieve → reason → act → reflect → flush)
                          ├── Tool System (Python REPL, Terminal, Web Fetch, File I/O)
                          ├── Multi-layer Memory (Daily Logs → MEMORY.md → RAG)
                          └── Multi-provider LLM (智谱, DeepSeek, OpenRouter, OpenAI, Ollama, SiliconFlow)
```

### Three Agent Engines

| Engine | File | Purpose |
|--------|------|---------|
| **LangGraph** | `backend/graph/engines/langgraph_engine.py` | Teaching core — 5-node StateGraph with retrieve/reason/act/reflect/flush |
| **create_react_agent** | `backend/graph/engines/create_agent_engine.py` | Production mode — LangGraph's prebuilt ReAct agent |
| **Raw Loop** | `backend/graph/engines/raw_loop_engine.py` | Minimal ~100-line while-loop, no LangChain dependency |

All three support **real token-level streaming** via SSE.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- An LLM API key (智谱 GLM free tier works)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env — at minimum set ZHIPUAI_API_KEY

# Start server
python -m uvicorn app:app --host 0.0.0.0 --port 8002
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### 3. Test

```bash
cd backend
pytest tests/ -v                              # All tests (65)
pytest tests/test_api_chat.py -v              # Chat API tests
pytest tests/test_config.py -k test_config_defaults  # Single test
```

## Project Structure

```
mini-openclaw/
├── backend/                  # FastAPI backend
│   ├── app.py               # Entry point, lifespan
│   ├── config.py             # Pydantic config with JSON persistence
│   ├── api/                  # REST + SSE endpoints
│   │   ├── chat.py           # POST /api/chat (SSE streaming)
│   │   ├── sessions.py       # Session CRUD + auto title
│   │   └── config_api.py     # Engine/memory/RAG switching
│   ├── graph/                # Agent core
│   │   ├── agent.py          # AgentManager — unified entry point
│   │   ├── engines/          # 3 interchangeable engines
│   │   ├── nodes/            # reason, act, retrieve, reflect, memory_flush
│   │   ├── session_manager.py
│   │   └── prompt_builder.py
│   ├── providers/            # LLM provider registry
│   │   ├── registry.py       # get_llm(), get_embeddings()
│   │   └── base.py           # ProviderSpec dataclass
│   ├── tools/                # Agent tools
│   │   ├── python_repl_tool.py  # Sandboxed eval/exec
│   │   ├── terminal_tool.py     # Allowlist-based shell
│   │   ├── fetch_url_tool.py    # Async HTTP fetch
│   │   └── file_tools.py        # Read/write/list
│   ├── memory/               # Multi-layer memory
│   │   └── native/           # Daily logs → MEMORY.md → RAG
│   ├── rag/                  # Hybrid BM25 + vector retrieval
│   └── tests/                # 65 tests
├── frontend/                 # Next.js 14 + Tailwind
│   └── src/
│       ├── app/              # App router
│       ├── components/       # Chat, Sidebar, MessageBubble, etc.
│       └── lib/              # api.ts, store.tsx (state management)
├── docs/                     # Reference documents
│   ├── plans/                # Design & implementation plans
│   └── *.pdf / *.png         # PRD, architecture diagrams
├── nanobot/                  # Reference: nanobot source code
└── docker-compose.yml
```

## Supported LLM Providers

| Provider | Default Model | Requires API Key |
|----------|--------------|-----------------|
| 智谱 (Zhipu) | glm-4.7-flash | Yes (`ZHIPUAI_API_KEY`) |
| DeepSeek | deepseek-chat | Yes (`DEEPSEEK_API_KEY`) |
| OpenRouter | claude-sonnet-4 | Yes (`OPENROUTER_API_KEY`) |
| OpenAI | gpt-4o | Yes (`OPENAI_API_KEY`) |
| SiliconFlow | Qwen2.5-7B | Yes (`SILICONFLOW_API_KEY`) |
| Ollama | qwen2.5:7b | No (local) |

Configure in `.env` — see `.env.example` for all options.

## Key Features

- **3 Agent Engines** — switch at runtime via sidebar dropdown
- **Real Streaming** — token-by-token SSE from LLM to browser
- **Tool Use** — Python REPL (sandboxed), terminal (allowlist), web fetch, file I/O
- **Multi-layer Memory** — daily logs auto-flushed to MEMORY.md via LLM curation
- **RAG Mode** — hybrid BM25 + vector retrieval (Milvus/FAISS/pgvector)
- **Session Management** — create, rename, delete, auto-title generation
- **Provider Hot-swap** — switch LLM providers without restart

## Reference Materials

The `docs/` and `nanobot/` directories contain pre-development reference materials:

- `docs/Mini-OpenClaw 开发需求文档 (PRD).pdf` — Original product requirements
- `docs/Mini-OpenClaw_README.pdf` — Original design reference
- `docs/工业级智能体记忆系统开发实践.pdf` — Memory system design reference
- `docs/openclaw架构图.png` / `nanobot架构图.png` — Architecture diagrams
- `nanobot/` — Full nanobot source code, used as implementation reference (see [deepwiki.com/HKUDS/nanobot](https://deepwiki.com/HKUDS/nanobot))

## License

Educational / research project.
