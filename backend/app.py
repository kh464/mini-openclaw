"""Mini-OpenClaw backend entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before any config/provider imports
load_dotenv()

from config import config
from graph.agent import AgentManager
from tools.skills_scanner import write_snapshot

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[startup] Mini-OpenClaw backend starting...")
    write_snapshot(BASE_DIR)

    agent_manager = AgentManager(base_dir=BASE_DIR, config=config)
    try:
        agent_manager.initialize()
        print(f"[startup] Agent engine: {config.agent_engine}")
    except Exception as e:
        print(f"[startup] Warning: Agent initialization failed: {e}")
        print("[startup] Chat will not work until LLM provider is configured.")

    app.state.agent_manager = agent_manager
    app.state.base_dir = BASE_DIR

    yield

    # Shutdown
    print("[shutdown] Mini-OpenClaw backend stopping...")


app = FastAPI(title="Mini-OpenClaw", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from api.chat import router as chat_router
from api.sessions import router as sessions_router
from api.files import router as files_router
from api.tokens import router as tokens_router
from api.compress import router as compress_router
from api.config_api import router as config_router
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(files_router)
app.include_router(tokens_router)
app.include_router(compress_router)
app.include_router(config_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "engine": config.agent_engine}
