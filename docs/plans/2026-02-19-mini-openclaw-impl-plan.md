# Mini-OpenClaw Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-stack AI Agent teaching/research system with three interchangeable agent engines, dual-layer memory, and IDE-style visualization.

**Architecture:** FastAPI backend serves SSE-streamed agent responses to a Next.js 14 frontend. Three agent engines (LangChain `create_agent`, LangGraph `StateGraph`, raw while-loop) share a unified interface. Dual-layer memory (Daily Logs + MEMORY.md) with Mem0 as alternate backend. Milvus Lite for vector storage.

**Tech Stack:** Python 3.10+ / FastAPI / LangChain 1.x / LangGraph / Next.js 14 / TypeScript / Shadcn/UI / Monaco Editor / Milvus Lite / tiktoken

**Design Doc:** `docs/plans/2026-02-19-mini-openclaw-design.md`

---

## Phase 1: Backend Foundation

### Task 1: Project Scaffold

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app.py`
- Create: `backend/__init__.py` (empty)
- Create: `backend/api/__init__.py` (empty)
- Create: `backend/graph/__init__.py` (empty)
- Create: `backend/graph/engines/__init__.py` (empty)
- Create: `backend/graph/nodes/__init__.py` (empty)
- Create: `backend/memory/__init__.py` (empty)
- Create: `backend/memory/native/__init__.py` (empty)
- Create: `backend/tools/__init__.py`
- Create: `backend/providers/__init__.py` (empty)
- Create: `backend/workspace/SOUL.md`
- Create: `backend/workspace/IDENTITY.md`
- Create: `backend/workspace/USER.md`
- Create: `backend/workspace/AGENTS.md`
- Create: `backend/memory/MEMORY.md`
- Create: `backend/skills/get_weather/SKILL.md`
- Create directories: `backend/sessions/`, `backend/sessions/archive/`, `backend/knowledge/`, `backend/storage/`, `backend/memory/logs/`
- Test: `backend/tests/test_scaffold.py`

**Step 1: Create requirements.txt**

```
# Core
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
httpx>=0.25.0

# LangChain ecosystem
langchain>=0.3.0
langchain-community>=0.3.0
langchain-openai>=0.3.0
langchain-milvus>=0.2.0
langgraph>=0.4.0
langgraph-prebuilt>=0.1.0

# Provider-specific LangChain integrations
langchain-deepseek>=0.1.0
langchain-ollama>=0.3.0

# RAG components
rank-bm25>=0.2.2

# Tools
html2text>=2024.2.0
beautifulsoup4>=4.12.0

# Token counting
tiktoken>=0.7.0

# Memory (Mem0 optional)
mem0ai>=0.1.0

# Milvus
pymilvus>=2.4.0

# Utilities
loguru>=0.7.0
json-repair>=0.30.0

# Dev
pytest>=7.0.0
pytest-asyncio>=0.21.0
ruff>=0.1.0
```

**Step 2: Create .env.example**

```
# Default LLM: 智谱 GLM-4-Flash
ZHIPUAI_API_KEY=your-zhipu-api-key

# Default Embedding: SiliconFlow BAAI/bge-m3
SILICONFLOW_API_KEY=your-siliconflow-api-key

# Optional providers (uncomment as needed)
# DEEPSEEK_API_KEY=your-deepseek-api-key
# OPENROUTER_API_KEY=your-openrouter-api-key
# OPENAI_API_KEY=your-openai-api-key

# Ollama (local, no key needed)
# OLLAMA_BASE_URL=http://localhost:11434
```

**Step 3: Create minimal app.py**

```python
"""Mini-OpenClaw backend entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: scan skills, initialize agent, build memory index
    print("[startup] Mini-OpenClaw backend starting...")
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


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

**Step 4: Create workspace template files**

`backend/workspace/SOUL.md`:
```markdown
# Soul

You are Mini-OpenClaw, a helpful and transparent AI assistant built for teaching and research.

## Personality
- Be concise, accurate, and friendly
- Explain your reasoning when using tools
- Always prioritize user safety

## Boundaries
- Never execute destructive commands without confirmation
- Be honest about limitations
```

`backend/workspace/IDENTITY.md`:
```markdown
# Identity

- Name: Mini-OpenClaw
- Role: Personal AI Assistant
- Style: Clear, structured responses with occasional emojis
```

`backend/workspace/USER.md`:
```markdown
# User Profile

(This file is populated as the agent learns about the user)
```

`backend/workspace/AGENTS.md`:
```markdown
# 操作指南

## 技能调用协议 (SKILL PROTOCOL)

你拥有一个技能列表 (SKILLS_SNAPSHOT)，其中列出了你可以使用的能力及其定义文件的位置。

**当你要使用某个技能时，必须严格遵守以下步骤：**
1. 你的第一步行动永远是使用 `read_file` 工具读取该技能对应的 `location` 路径下的 Markdown 文件。
2. 仔细阅读文件中的内容、步骤和示例。
3. 根据文件中的指示，结合你内置的 Core Tools (terminal, python_repl, fetch_url) 来执行具体任务。

**禁止**直接猜测技能的参数或用法，必须先读取文件！

## 记忆协议

当你在对话中发现以下类型的信息时，应主动记录到记忆系统：
- 用户的偏好和习惯
- 项目关键事实
- 成功的工具调用经验
- 重要的决策和原因
```

`backend/memory/MEMORY.md`:
```markdown
# Long-term Memory

## User Preferences

(No preferences recorded yet)

## Project Facts

(No project facts recorded yet)

## Learned Skills

(No skills learned yet)
```

`backend/skills/get_weather/SKILL.md`:
```markdown
---
name: get_weather
description: 查询指定城市的实时天气信息
---

## 步骤

1. 使用 `fetch_url` 工具访问 `https://wttr.in/{城市名}?format=3`
2. 解析返回的天气数据
3. 以友好的格式回复用户

## 示例

查询北京天气: `fetch_url("https://wttr.in/Beijing?format=3")`
```

**Step 5: Create scaffold test**

```python
# backend/tests/test_scaffold.py
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def test_directory_structure():
    dirs = [
        "api", "graph", "graph/engines", "graph/nodes",
        "memory", "memory/native", "memory/logs",
        "tools", "providers", "workspace", "skills",
        "sessions", "sessions/archive", "knowledge", "storage",
    ]
    for d in dirs:
        assert (BASE / d).is_dir(), f"Missing directory: {d}"


def test_workspace_files_exist():
    files = ["SOUL.md", "IDENTITY.md", "USER.md", "AGENTS.md"]
    for f in files:
        assert (BASE / "workspace" / f).is_file(), f"Missing: workspace/{f}"


def test_memory_file_exists():
    assert (BASE / "memory" / "MEMORY.md").is_file()


def test_skill_exists():
    assert (BASE / "skills" / "get_weather" / "SKILL.md").is_file()
```

**Step 6: Create all directories, run test**

```bash
cd backend
mkdir -p api graph/engines graph/nodes memory/native memory/logs tools providers workspace skills/get_weather sessions/archive knowledge storage tests
touch __init__.py api/__init__.py graph/__init__.py graph/engines/__init__.py graph/nodes/__init__.py memory/__init__.py memory/native/__init__.py tools/__init__.py providers/__init__.py
pip install -r requirements.txt
pytest tests/test_scaffold.py -v
```

Expected: All tests PASS.

**Step 7: Verify FastAPI starts**

```bash
cd backend
uvicorn app:app --port 8002 --reload &
curl http://localhost:8002/api/health
# Expected: {"status":"ok"}
```

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: backend project scaffold with directories, deps, workspace templates"
```

---

### Task 2: Configuration System

**Files:**
- Create: `backend/config.py`
- Test: `backend/tests/test_config.py`

**Step 1: Write the test**

```python
# backend/tests/test_config.py
import json
import tempfile
from pathlib import Path


def test_config_defaults():
    from config import AppConfig
    cfg = AppConfig()
    assert cfg.agent_engine == "langgraph"
    assert cfg.memory_backend == "native"
    assert cfg.vector_store == "milvus"
    assert cfg.rag_mode is False
    assert cfg.llm.provider == "zhipu"
    assert cfg.llm.model == "glm-4-flash"
    assert cfg.embedding.provider == "siliconflow"
    assert cfg.embedding.model == "BAAI/bge-m3"


def test_config_save_and_load():
    from config import AppConfig, load_config, save_config

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "config.json"
        cfg = AppConfig()
        cfg.rag_mode = True
        save_config(cfg, path)

        loaded = load_config(path)
        assert loaded.rag_mode is True
        assert loaded.llm.provider == "zhipu"


def test_config_partial_update():
    from config import AppConfig, load_config, save_config

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "config.json"
        # Write partial config
        path.write_text(json.dumps({"agent_engine": "raw_loop"}))
        loaded = load_config(path)
        assert loaded.agent_engine == "raw_loop"
        # Defaults preserved
        assert loaded.llm.model == "glm-4-flash"
```

**Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

**Step 3: Implement config.py**

```python
"""Global configuration with JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_BASE_DIR = Path(__file__).resolve().parent
_DEFAULT_CONFIG_PATH = _BASE_DIR / "config.json"


class LLMConfig(BaseModel):
    provider: str = "zhipu"
    model: str = "glm-4-flash"
    temperature: float = 0.7
    max_tokens: int = 4096


class EmbeddingConfig(BaseModel):
    provider: str = "siliconflow"
    model: str = "BAAI/bge-m3"
    api_base: str = "https://api.siliconflow.cn/v1"


class ProviderCreds(BaseModel):
    api_key: str = ""
    api_base: str = ""


class AppConfig(BaseModel):
    agent_engine: Literal["create_agent", "langgraph", "raw_loop"] = "langgraph"
    memory_backend: Literal["native", "mem0"] = "native"
    vector_store: Literal["milvus", "pgvector", "faiss"] = "milvus"
    rag_mode: bool = False
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    providers: dict[str, ProviderCreds] = Field(default_factory=dict)


def load_config(path: Path = _DEFAULT_CONFIG_PATH) -> AppConfig:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig.model_validate(data)
    return AppConfig()


def save_config(cfg: AppConfig, path: Path = _DEFAULT_CONFIG_PATH) -> None:
    path.write_text(
        cfg.model_dump_json(indent=2),
        encoding="utf-8",
    )


# Singleton — imported by other modules
config = load_config()
```

**Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_config.py -v
```

Expected: All PASS.

**Step 5: Commit**

```bash
git add backend/config.py backend/tests/test_config.py
git commit -m "feat: configuration system with JSON persistence and Pydantic schema"
```

---

### Task 3: Provider Registry + LLM/Embedding Abstraction

**Files:**
- Create: `backend/providers/registry.py`
- Create: `backend/providers/base.py`
- Create: `backend/providers/embedding.py`
- Test: `backend/tests/test_providers.py`

**Step 1: Write the test**

```python
# backend/tests/test_providers.py
from providers.registry import PROVIDERS, get_provider_spec, get_llm, get_embeddings


def test_registry_has_providers():
    names = [p.name for p in PROVIDERS]
    assert "zhipu" in names
    assert "deepseek" in names
    assert "openrouter" in names
    assert "ollama" in names
    assert "openai" in names


def test_get_provider_spec():
    spec = get_provider_spec("zhipu")
    assert spec is not None
    assert spec.display_name == "智谱 GLM"

    assert get_provider_spec("nonexistent") is None


def test_get_llm_returns_chat_model(monkeypatch):
    """Verify get_llm returns a LangChain BaseChatModel (mocked)."""
    monkeypatch.setenv("ZHIPUAI_API_KEY", "test-key")
    # Just verify it doesn't crash on import resolution
    from providers.registry import _resolve_class
    # Test the class resolver with a known class
    cls = _resolve_class("langchain_openai.ChatOpenAI")
    assert cls is not None
```

**Step 2: Implement providers**

`backend/providers/base.py`:
```python
"""Provider base types."""

from dataclasses import dataclass, field


@dataclass
class ProviderSpec:
    name: str
    llm_class: str
    env_key: str | None
    display_name: str
    default_model: str
    supports_embedding: bool = False
    embedding_class: str | None = None
    api_base_default: str = ""
    extra_init_kwargs: dict = field(default_factory=dict)
```

`backend/providers/registry.py`:
```python
"""Provider registry — single source of truth for all LLM/Embedding providers."""

from __future__ import annotations

import importlib
import os
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from providers.base import ProviderSpec
from config import config, AppConfig

PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="zhipu",
        llm_class="langchain_community.chat_models.ChatZhipuAI",
        env_key="ZHIPUAI_API_KEY",
        display_name="智谱 GLM",
        default_model="glm-4-flash",
    ),
    ProviderSpec(
        name="deepseek",
        llm_class="langchain_openai.ChatOpenAI",
        env_key="DEEPSEEK_API_KEY",
        display_name="DeepSeek",
        default_model="deepseek-chat",
        api_base_default="https://api.deepseek.com/v1",
    ),
    ProviderSpec(
        name="openrouter",
        llm_class="langchain_openai.ChatOpenAI",
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        default_model="anthropic/claude-sonnet-4",
        api_base_default="https://openrouter.ai/api/v1",
    ),
    ProviderSpec(
        name="openai",
        llm_class="langchain_openai.ChatOpenAI",
        env_key="OPENAI_API_KEY",
        display_name="OpenAI",
        default_model="gpt-4o",
        supports_embedding=True,
        embedding_class="langchain_openai.OpenAIEmbeddings",
    ),
    ProviderSpec(
        name="ollama",
        llm_class="langchain_ollama.ChatOllama",
        env_key=None,
        display_name="Ollama (本地)",
        default_model="qwen2.5:7b",
        supports_embedding=True,
        embedding_class="langchain_ollama.OllamaEmbeddings",
        api_base_default="http://localhost:11434",
    ),
    ProviderSpec(
        name="siliconflow",
        llm_class="langchain_openai.ChatOpenAI",
        env_key="SILICONFLOW_API_KEY",
        display_name="SiliconFlow",
        default_model="Qwen/Qwen2.5-7B-Instruct",
        supports_embedding=True,
        embedding_class="langchain_openai.OpenAIEmbeddings",
        api_base_default="https://api.siliconflow.cn/v1",
    ),
]


def get_provider_spec(name: str) -> ProviderSpec | None:
    return next((p for p in PROVIDERS if p.name == name), None)


def _resolve_class(dotted_path: str) -> type:
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_llm(cfg: AppConfig | None = None) -> BaseChatModel:
    cfg = cfg or config
    spec = get_provider_spec(cfg.llm.provider)
    if spec is None:
        raise ValueError(f"Unknown LLM provider: {cfg.llm.provider}")

    cls = _resolve_class(spec.llm_class)
    kwargs: dict[str, Any] = {
        "model": cfg.llm.model or spec.default_model,
        "temperature": cfg.llm.temperature,
        "max_tokens": cfg.llm.max_tokens,
        "streaming": True,
    }

    # API key
    api_key = None
    if spec.env_key:
        api_key = os.getenv(spec.env_key) or cfg.providers.get(spec.name, None)
        if api_key and hasattr(api_key, "api_key"):
            api_key = api_key.api_key
        if isinstance(api_key, str) and api_key:
            kwargs["api_key"] = api_key

    # API base
    creds = cfg.providers.get(spec.name)
    api_base = (creds.api_base if creds and creds.api_base else "") or spec.api_base_default
    if api_base:
        kwargs["base_url"] = api_base

    return cls(**kwargs)


def get_embeddings(cfg: AppConfig | None = None) -> Embeddings:
    cfg = cfg or config
    emb_cfg = cfg.embedding

    # SiliconFlow uses OpenAI-compatible endpoint
    if emb_cfg.provider == "siliconflow":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=emb_cfg.model,
            openai_api_key=os.getenv("SILICONFLOW_API_KEY", ""),
            openai_api_base=emb_cfg.api_base,
        )

    spec = get_provider_spec(emb_cfg.provider)
    if spec and spec.embedding_class:
        cls = _resolve_class(spec.embedding_class)
        kwargs = {"model": emb_cfg.model}
        if emb_cfg.api_base:
            kwargs["base_url"] = emb_cfg.api_base
        return cls(**kwargs)

    raise ValueError(f"No embedding support for provider: {emb_cfg.provider}")
```

**Step 3: Run tests**

```bash
cd backend && pytest tests/test_providers.py -v
```

**Step 4: Commit**

```bash
git add backend/providers/
git commit -m "feat: provider registry with LLM and embedding abstraction"
```

---

## Phase 2: Core Tools

### Task 4: Terminal, Python REPL, Read File Tools

**Files:**
- Create: `backend/tools/terminal_tool.py`
- Create: `backend/tools/python_repl_tool.py`
- Create: `backend/tools/read_file_tool.py`
- Modify: `backend/tools/__init__.py`
- Test: `backend/tests/test_tools_basic.py`

**Step 1: Write tests**

```python
# backend/tests/test_tools_basic.py
import tempfile
from pathlib import Path

import pytest


def test_terminal_echo():
    from tools.terminal_tool import create_terminal_tool
    with tempfile.TemporaryDirectory() as td:
        tool = create_terminal_tool(root_dir=td)
        result = tool.invoke({"command": "echo hello"})
        assert "hello" in result


def test_terminal_blocks_dangerous():
    from tools.terminal_tool import create_terminal_tool
    with tempfile.TemporaryDirectory() as td:
        tool = create_terminal_tool(root_dir=td)
        result = tool.invoke({"command": "rm -rf /"})
        assert "blocked" in result.lower() or "denied" in result.lower()


def test_read_file():
    from tools.read_file_tool import create_read_file_tool
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "test.txt").write_text("hello world")
        tool = create_read_file_tool(root_dir=td)
        result = tool.invoke({"path": "test.txt"})
        assert "hello world" in result


def test_read_file_blocks_traversal():
    from tools.read_file_tool import create_read_file_tool
    with tempfile.TemporaryDirectory() as td:
        tool = create_read_file_tool(root_dir=td)
        result = tool.invoke({"path": "../../etc/passwd"})
        assert "denied" in result.lower() or "error" in result.lower()


def test_python_repl():
    from tools.python_repl_tool import create_python_repl_tool
    tool = create_python_repl_tool()
    result = tool.invoke({"code": "print(2 + 3)"})
    assert "5" in result
```

**Step 2: Implement terminal_tool.py**

```python
"""Sandboxed terminal tool."""

import subprocess
from pathlib import Path

from langchain_core.tools import tool as lc_tool, BaseTool

BLOCKED_COMMANDS = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", "shutdown",
    ":(){", "fork bomb", "> /dev/sda", "chmod -R 777 /",
]
MAX_OUTPUT = 5000
TIMEOUT = 30


def create_terminal_tool(root_dir: str) -> BaseTool:
    root = Path(root_dir).resolve()

    @lc_tool
    def terminal(command: str) -> str:
        """Execute a shell command in a sandboxed environment. Use for system operations."""
        cmd_lower = command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return f"⛔ Blocked: dangerous command detected."
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=TIMEOUT, cwd=str(root),
            )
            output = (result.stdout + result.stderr).strip()
            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + "\n...[truncated]"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "⛔ Command timed out (30s limit)."
        except Exception as e:
            return f"Error: {e}"

    return terminal
```

**Step 3: Implement read_file_tool.py**

```python
"""Sandboxed file reader tool."""

from pathlib import Path

from langchain_core.tools import tool as lc_tool, BaseTool

MAX_OUTPUT = 10000


def create_read_file_tool(root_dir: str) -> BaseTool:
    root = Path(root_dir).resolve()

    @lc_tool
    def read_file(path: str) -> str:
        """Read the contents of a file within the project directory."""
        target = (root / path).resolve()
        if not str(target).startswith(str(root)):
            return "⛔ Access denied: path traversal detected."
        if not target.is_file():
            return f"Error: file not found: {path}"
        try:
            content = target.read_text(encoding="utf-8")
            if len(content) > MAX_OUTPUT:
                content = content[:MAX_OUTPUT] + "\n...[truncated]"
            return content
        except Exception as e:
            return f"Error reading file: {e}"

    return read_file
```

**Step 4: Implement python_repl_tool.py**

```python
"""Python REPL tool."""

import io
import contextlib

from langchain_core.tools import tool as lc_tool, BaseTool

MAX_OUTPUT = 5000


def create_python_repl_tool() -> BaseTool:

    @lc_tool
    def python_repl(code: str) -> str:
        """Execute Python code and return the output. Use for calculations and data processing."""
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, {"__builtins__": __builtins__})
            output = stdout.getvalue().strip()
            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + "\n...[truncated]"
            return output or "(no output)"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    return python_repl
```

**Step 5: Update tools/__init__.py**

```python
"""Tool registration factory."""

from pathlib import Path

from langchain_core.tools import BaseTool

from tools.terminal_tool import create_terminal_tool
from tools.python_repl_tool import create_python_repl_tool
from tools.read_file_tool import create_read_file_tool


def get_all_tools(base_dir: str | Path) -> list[BaseTool]:
    base_dir = str(Path(base_dir).resolve())
    tools = [
        create_terminal_tool(root_dir=base_dir),
        create_python_repl_tool(),
        create_read_file_tool(root_dir=base_dir),
    ]
    # fetch_url and search_knowledge added in Task 5
    return tools
```

**Step 6: Run tests, commit**

```bash
cd backend && pytest tests/test_tools_basic.py -v
git add backend/tools/ backend/tests/test_tools_basic.py
git commit -m "feat: terminal, python REPL, and read_file core tools"
```

---

### Task 5: Fetch URL, Search Knowledge Tools + Skills Scanner

**Files:**
- Create: `backend/tools/fetch_url_tool.py`
- Create: `backend/tools/search_knowledge_tool.py`
- Create: `backend/tools/skills_scanner.py`
- Modify: `backend/tools/__init__.py`
- Test: `backend/tests/test_tools_advanced.py`

**Step 1: Implement fetch_url_tool.py**

```python
"""Web fetch tool — fetches URL content and converts HTML to Markdown."""

import httpx
import html2text

from langchain_core.tools import tool as lc_tool, BaseTool

MAX_OUTPUT = 5000
TIMEOUT = 15


def create_fetch_url_tool() -> BaseTool:

    @lc_tool
    def fetch_url(url: str) -> str:
        """Fetch a URL and return its content as clean Markdown text."""
        try:
            resp = httpx.get(url, timeout=TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

            if "json" in content_type:
                text = resp.text
            else:
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.body_width = 0
                text = h.handle(resp.text)

            if len(text) > MAX_OUTPUT:
                text = text[:MAX_OUTPUT] + "\n...[truncated]"
            return text.strip()
        except httpx.TimeoutException:
            return "Error: request timed out (15s limit)."
        except Exception as e:
            return f"Error fetching URL: {e}"

    return fetch_url
```

**Step 2: Implement skills_scanner.py**

```python
"""Scans skills/ directory and generates SKILLS_SNAPSHOT.md."""

import re
from pathlib import Path


def scan_skills(skills_dir: str | Path) -> list[dict]:
    """Scan skills directory, parse YAML frontmatter, return list of skill metadata."""
    skills = []
    skills_path = Path(skills_dir)
    if not skills_path.is_dir():
        return skills

    for skill_md in sorted(skills_path.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        if meta:
            meta["location"] = f"./skills/{skill_md.parent.name}/SKILL.md"
            skills.append(meta)
    return skills


def _parse_frontmatter(text: str) -> dict | None:
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    result = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip()
    return result


def generate_snapshot(skills: list[dict]) -> str:
    """Generate SKILLS_SNAPSHOT.md content."""
    lines = ["<available_skills>"]
    for s in skills:
        lines.append("  <skill>")
        lines.append(f"    <name>{s.get('name', 'unknown')}</name>")
        lines.append(f"    <description>{s.get('description', '')}</description>")
        lines.append(f"    <location>{s.get('location', '')}</location>")
        lines.append("  </skill>")
    lines.append("</available_skills>")
    return "\n".join(lines)


def write_snapshot(base_dir: str | Path) -> str:
    """Scan skills and write SKILLS_SNAPSHOT.md. Returns the content."""
    base = Path(base_dir)
    skills = scan_skills(base / "skills")
    content = generate_snapshot(skills)
    (base / "SKILLS_SNAPSHOT.md").write_text(content, encoding="utf-8")
    return content
```

**Step 3: Implement search_knowledge_tool.py (placeholder — full RAG in Task 13)**

```python
"""Knowledge base search tool — placeholder until RAG is wired in Task 13."""

from langchain_core.tools import tool as lc_tool, BaseTool


def create_search_knowledge_tool(retriever=None) -> BaseTool:

    @lc_tool
    def search_knowledge_base(query: str) -> str:
        """Search the knowledge base for relevant information using hybrid retrieval."""
        if retriever is None:
            return "(Knowledge base not yet initialized. Place documents in knowledge/ directory.)"
        try:
            docs = retriever.invoke(query)
            if not docs:
                return "No relevant results found."
            results = []
            for i, doc in enumerate(docs[:3], 1):
                source = doc.metadata.get("source", "unknown")
                results.append(f"[{i}] {source}\n{doc.page_content[:500]}")
            return "\n---\n".join(results)
        except Exception as e:
            return f"Search error: {e}"

    return search_knowledge_base
```

**Step 4: Update tools/__init__.py to include all 5**

```python
"""Tool registration factory."""

from pathlib import Path

from langchain_core.tools import BaseTool

from tools.terminal_tool import create_terminal_tool
from tools.python_repl_tool import create_python_repl_tool
from tools.read_file_tool import create_read_file_tool
from tools.fetch_url_tool import create_fetch_url_tool
from tools.search_knowledge_tool import create_search_knowledge_tool


def get_all_tools(base_dir: str | Path, retriever=None) -> list[BaseTool]:
    base_dir = str(Path(base_dir).resolve())
    return [
        create_terminal_tool(root_dir=base_dir),
        create_python_repl_tool(),
        create_read_file_tool(root_dir=base_dir),
        create_fetch_url_tool(),
        create_search_knowledge_tool(retriever=retriever),
    ]
```

**Step 5: Write test and run**

```python
# backend/tests/test_tools_advanced.py
from tools.skills_scanner import scan_skills, generate_snapshot, write_snapshot
from pathlib import Path
import tempfile


def test_skills_scanner():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        skill_dir = base / "skills" / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test\ndescription: a test skill\n---\n\nHello"
        )
        skills = scan_skills(base / "skills")
        assert len(skills) == 1
        assert skills[0]["name"] == "test"


def test_generate_snapshot():
    skills = [{"name": "weather", "description": "Get weather", "location": "./skills/weather/SKILL.md"}]
    snap = generate_snapshot(skills)
    assert "<name>weather</name>" in snap
    assert "<available_skills>" in snap


def test_write_snapshot():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "skills" / "demo").mkdir(parents=True)
        (base / "skills" / "demo" / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo skill\n---\n"
        )
        content = write_snapshot(base)
        assert "<name>demo</name>" in content
        assert (base / "SKILLS_SNAPSHOT.md").exists()


def test_fetch_url_tool_exists():
    from tools.fetch_url_tool import create_fetch_url_tool
    tool = create_fetch_url_tool()
    assert tool.name == "fetch_url"


def test_search_knowledge_tool_no_retriever():
    from tools.search_knowledge_tool import create_search_knowledge_tool
    tool = create_search_knowledge_tool(retriever=None)
    result = tool.invoke({"query": "test"})
    assert "not yet initialized" in result.lower()
```

```bash
cd backend && pytest tests/test_tools_advanced.py -v
git add backend/tools/ backend/tests/test_tools_advanced.py
git commit -m "feat: fetch_url, search_knowledge tools and skills scanner"
```

---

## Phase 3: Session + Prompt

### Task 6: Session Manager

**Files:**
- Create: `backend/graph/session_manager.py`
- Test: `backend/tests/test_session_manager.py`

**Step 1: Write test**

```python
# backend/tests/test_session_manager.py
import tempfile
from pathlib import Path


def test_create_and_load_session():
    from graph.session_manager import SessionManager
    with tempfile.TemporaryDirectory() as td:
        sm = SessionManager(sessions_dir=td)
        sid = sm.create_session()
        assert sid is not None
        messages = sm.load_session(sid)
        assert messages == []


def test_save_and_load_messages():
    from graph.session_manager import SessionManager
    with tempfile.TemporaryDirectory() as td:
        sm = SessionManager(sessions_dir=td)
        sid = sm.create_session()
        sm.save_message(sid, "user", "Hello")
        sm.save_message(sid, "assistant", "Hi there!")
        messages = sm.load_session(sid)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"


def test_list_sessions():
    from graph.session_manager import SessionManager
    with tempfile.TemporaryDirectory() as td:
        sm = SessionManager(sessions_dir=td)
        sm.create_session()
        sm.create_session()
        sessions = sm.list_sessions()
        assert len(sessions) == 2


def test_compress_history():
    from graph.session_manager import SessionManager
    with tempfile.TemporaryDirectory() as td:
        sm = SessionManager(sessions_dir=td)
        sid = sm.create_session()
        for i in range(6):
            sm.save_message(sid, "user" if i % 2 == 0 else "assistant", f"msg {i}")
        archived = sm.compress_history(sid, summary="Summary of conversation", n=4)
        assert archived == 4
        remaining = sm.load_session(sid)
        assert len(remaining) == 2  # 6 - 4 = 2
        ctx = sm.get_compressed_context(sid)
        assert "Summary of conversation" in ctx
```

**Step 2: Implement session_manager.py**

```python
"""Session persistence — JSON file per session."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


class SessionManager:
    def __init__(self, sessions_dir: str | Path):
        self.dir = Path(sessions_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "archive").mkdir(exist_ok=True)

    def create_session(self, title: str = "New Chat") -> str:
        sid = uuid.uuid4().hex[:12]
        data = {
            "title": title,
            "created_at": time.time(),
            "updated_at": time.time(),
            "compressed_context": "",
            "messages": [],
        }
        self._write(sid, data)
        return sid

    def load_session(self, sid: str) -> list[dict]:
        data = self._read(sid)
        return data.get("messages", [])

    def load_session_for_agent(self, sid: str) -> list[dict]:
        """Return messages optimized for LLM: merge consecutive assistant msgs, inject compressed context."""
        data = self._read(sid)
        messages = data.get("messages", [])
        compressed = data.get("compressed_context", "")

        merged = self._merge_consecutive_assistant(messages)

        if compressed:
            merged.insert(0, {
                "role": "assistant",
                "content": f"[以下是之前对话的摘要]\n{compressed}",
            })
        return merged

    def save_message(self, sid: str, role: str, content: str, tool_calls: list | None = None):
        data = self._read(sid)
        msg: dict = {"role": role, "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        data["messages"].append(msg)
        data["updated_at"] = time.time()
        self._write(sid, data)

    def list_sessions(self) -> list[dict]:
        sessions = []
        for f in sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "id": f.stem,
                "title": data.get("title", "Untitled"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "message_count": len(data.get("messages", [])),
            })
        return sessions

    def rename_session(self, sid: str, title: str):
        data = self._read(sid)
        data["title"] = title
        self._write(sid, data)

    def delete_session(self, sid: str):
        path = self.dir / f"{sid}.json"
        if path.exists():
            path.unlink()

    def compress_history(self, sid: str, summary: str, n: int) -> int:
        data = self._read(sid)
        messages = data["messages"]
        if len(messages) < n:
            return 0

        archived = messages[:n]
        archive_path = self.dir / "archive" / f"{sid}_{int(time.time())}.json"
        archive_path.write_text(json.dumps(archived, ensure_ascii=False, indent=2), encoding="utf-8")

        data["messages"] = messages[n:]
        existing = data.get("compressed_context", "")
        data["compressed_context"] = f"{existing}\n---\n{summary}".strip() if existing else summary
        self._write(sid, data)
        return n

    def get_compressed_context(self, sid: str) -> str:
        data = self._read(sid)
        return data.get("compressed_context", "")

    def _merge_consecutive_assistant(self, messages: list[dict]) -> list[dict]:
        if not messages:
            return []
        merged = [messages[0].copy()]
        for msg in messages[1:]:
            if msg["role"] == "assistant" and merged[-1]["role"] == "assistant":
                merged[-1]["content"] += "\n" + msg["content"]
            else:
                merged.append(msg.copy())
        return merged

    def _read(self, sid: str) -> dict:
        path = self.dir / f"{sid}.json"
        if not path.exists():
            return {"messages": [], "compressed_context": ""}
        data = json.loads(path.read_text(encoding="utf-8"))
        # v1 migration: bare list → v2 dict
        if isinstance(data, list):
            data = {"messages": data, "compressed_context": ""}
        return data

    def _write(self, sid: str, data: dict):
        path = self.dir / f"{sid}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

**Step 3: Run tests, commit**

```bash
cd backend && pytest tests/test_session_manager.py -v
git add backend/graph/session_manager.py backend/tests/test_session_manager.py
git commit -m "feat: session manager with JSON persistence and compression"
```

---

### Task 7: Prompt Builder

**Files:**
- Create: `backend/graph/prompt_builder.py`
- Test: `backend/tests/test_prompt_builder.py`

**Step 1: Write test**

```python
# backend/tests/test_prompt_builder.py
import tempfile
from pathlib import Path


def test_build_system_prompt():
    from graph.prompt_builder import PromptBuilder
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "workspace").mkdir()
        (base / "workspace" / "SOUL.md").write_text("# Soul\nBe kind.")
        (base / "workspace" / "IDENTITY.md").write_text("# Identity\nI am Bot.")
        (base / "workspace" / "USER.md").write_text("# User\nUnknown.")
        (base / "workspace" / "AGENTS.md").write_text("# Agents\nFollow rules.")
        (base / "memory").mkdir()
        (base / "memory" / "MEMORY.md").write_text("# Memory\nEmpty.")
        (base / "SKILLS_SNAPSHOT.md").write_text("<available_skills></available_skills>")

        pb = PromptBuilder(base_dir=td)
        prompt = pb.build()
        assert "Soul" in prompt
        assert "Identity" in prompt
        assert "Memory" in prompt
        assert "available_skills" in prompt


def test_truncation():
    from graph.prompt_builder import PromptBuilder
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "workspace").mkdir()
        # Create oversized file
        (base / "workspace" / "SOUL.md").write_text("X" * 25000)
        (base / "workspace" / "IDENTITY.md").write_text("ok")
        (base / "workspace" / "USER.md").write_text("ok")
        (base / "workspace" / "AGENTS.md").write_text("ok")
        (base / "memory").mkdir()
        (base / "memory" / "MEMORY.md").write_text("ok")
        (base / "SKILLS_SNAPSHOT.md").write_text("ok")

        pb = PromptBuilder(base_dir=td)
        prompt = pb.build()
        assert "...[truncated]" in prompt
```

**Step 2: Implement prompt_builder.py**

```python
"""System Prompt assembler — 6 components in fixed order."""

from pathlib import Path

MAX_COMPONENT_CHARS = 20000


class PromptBuilder:
    def __init__(self, base_dir: str | Path):
        self.base = Path(base_dir)

    def build(self, rag_mode: bool = False) -> str:
        components = [
            ("Skills Snapshot", self.base / "SKILLS_SNAPSHOT.md"),
            ("Soul", self.base / "workspace" / "SOUL.md"),
            ("Identity", self.base / "workspace" / "IDENTITY.md"),
            ("User Profile", self.base / "workspace" / "USER.md"),
            ("Agents Guide", self.base / "workspace" / "AGENTS.md"),
        ]

        if rag_mode:
            components.append(("RAG Mode", None))  # Placeholder text
        else:
            components.append(("Long-term Memory", self.base / "memory" / "MEMORY.md"))

        sections = []
        for label, path in components:
            if path is None:
                content = (
                    "你的长期记忆将通过 RAG 检索动态注入，无需在此加载完整记忆文件。"
                    "当你需要回忆过去的信息时，系统会自动检索相关记忆片段。"
                )
            elif path.is_file():
                content = path.read_text(encoding="utf-8")
                if len(content) > MAX_COMPONENT_CHARS:
                    content = content[:MAX_COMPONENT_CHARS] + "\n...[truncated]"
            else:
                content = f"(File not found: {path.name})"

            sections.append(f"<!-- {label} -->\n{content}")

        return "\n\n".join(sections)
```

**Step 3: Run tests, commit**

```bash
cd backend && pytest tests/test_prompt_builder.py -v
git add backend/graph/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat: prompt builder with 6-component assembly and truncation"
```

---

## Phase 4: Agent Engines

### Task 8: BaseEngine + Raw Loop Engine

**Files:**
- Create: `backend/graph/engines/base.py`
- Create: `backend/graph/engines/raw_loop_engine.py`
- Test: `backend/tests/test_raw_loop.py`

**Step 1: Implement BaseEngine**

```python
# backend/graph/engines/base.py
"""Abstract base for all agent engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass
class AgentEvent:
    """Unified event emitted by all engines."""
    type: str  # "token" | "tool_start" | "tool_end" | "new_response" | "retrieval" | "done" | "error"
    data: dict[str, Any]


class BaseEngine(ABC):
    @abstractmethod
    async def astream(
        self,
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> AsyncIterator[AgentEvent]:
        """Stream agent events for a single user message."""
        ...
```

**Step 2: Implement raw_loop_engine.py**

```python
# backend/graph/engines/raw_loop_engine.py
"""Self-built agent loop — no LangChain dependency. ~100 lines of core logic."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from graph.engines.base import BaseEngine, AgentEvent

MAX_ITERATIONS = 20


class RawLoopEngine(BaseEngine):
    def __init__(self, api_base: str, api_key: str, model: str, tools: list[dict],
                 tool_executor: dict):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.tools_schema = tools       # OpenAI-format tool schemas
        self.tool_executor = tool_executor  # name → callable

    async def astream(
        self,
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> AsyncIterator[AgentEvent]:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        for iteration in range(MAX_ITERATIONS):
            response = await self._call_llm(messages)

            # Yield text tokens
            content = response.get("content", "")
            if content:
                yield AgentEvent(type="token", data={"content": content})

            # Check for tool calls
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                break

            # Process each tool call
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])

                yield AgentEvent(type="tool_start", data={"tool": fn_name, "input": fn_args})

                executor = self.tool_executor.get(fn_name)
                if executor:
                    result = await executor(**fn_args) if callable(executor) else str(executor)
                else:
                    result = f"Error: unknown tool '{fn_name}'"

                yield AgentEvent(type="tool_end", data={"tool": fn_name, "output": str(result)})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result),
                })

            yield AgentEvent(type="new_response", data={})

        yield AgentEvent(type="done", data={"content": content})

    async def _call_llm(self, messages: list[dict]) -> dict:
        """Call OpenAI-compatible chat completion API (non-streaming for simplicity)."""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": self.tools_schema if self.tools_schema else None,
        }
        if not payload["tools"]:
            del payload["tools"]

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]
        return {
            "content": choice.get("content", ""),
            "tool_calls": choice.get("tool_calls", []),
        }
```

**Step 3: Write test**

```python
# backend/tests/test_raw_loop.py
import pytest
from graph.engines.base import AgentEvent


def test_agent_event_creation():
    event = AgentEvent(type="token", data={"content": "hello"})
    assert event.type == "token"
    assert event.data["content"] == "hello"


def test_raw_loop_engine_instantiation():
    from graph.engines.raw_loop_engine import RawLoopEngine
    engine = RawLoopEngine(
        api_base="http://localhost:8000/v1",
        api_key="test",
        model="test-model",
        tools=[],
        tool_executor={},
    )
    assert engine.model == "test-model"
```

**Step 4: Run tests, commit**

```bash
cd backend && pytest tests/test_raw_loop.py -v
git add backend/graph/engines/
git commit -m "feat: BaseEngine interface and raw loop agent engine"
```

---

### Task 9: LangGraph Engine + Custom Nodes

**Files:**
- Create: `backend/graph/nodes/reason.py`
- Create: `backend/graph/nodes/act.py`
- Create: `backend/graph/nodes/retrieve.py`
- Create: `backend/graph/nodes/reflect.py`
- Create: `backend/graph/nodes/memory_flush.py`
- Create: `backend/graph/engines/langgraph_engine.py`
- Test: `backend/tests/test_langgraph_engine.py`

**Step 1: Implement nodes**

`backend/graph/nodes/reason.py`:
```python
"""LLM reasoning node — calls the model and returns response."""

from langchain_core.messages import AIMessage


async def reason_node(state: dict) -> dict:
    """Call LLM with current messages. Returns updated state with AI response."""
    llm = state["llm"]
    messages = state["messages"]
    tools = state.get("tools", [])

    if tools:
        llm_with_tools = llm.bind_tools(tools)
        response: AIMessage = await llm_with_tools.ainvoke(messages)
    else:
        response = await llm.ainvoke(messages)

    return {"messages": messages + [response], "last_response": response}
```

`backend/graph/nodes/act.py`:
```python
"""Tool execution node — runs tool calls from the last AI message."""

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

    return {"messages": messages}
```

`backend/graph/nodes/retrieve.py`:
```python
"""RAG retrieval node — runs hybrid search before LLM reasoning."""


async def retrieve_node(state: dict) -> dict:
    """Retrieve relevant memory/knowledge and inject into messages."""
    retriever = state.get("retriever")
    if not retriever:
        return state

    query = state["messages"][-1].content if state["messages"] else ""
    docs = retriever.invoke(query)

    if docs:
        context_parts = [f"[{i+1}] {d.page_content[:500]}" for i, d in enumerate(docs[:3])]
        context_text = "\n---\n".join(context_parts)
        retrieval_msg = f"[记忆检索结果]\n{context_text}"

        from langchain_core.messages import SystemMessage
        messages = list(state["messages"])
        messages.insert(-1, SystemMessage(content=retrieval_msg))
        return {
            **state,
            "messages": messages,
            "retrieval_results": [{"text": d.page_content, "score": d.metadata.get("score", 0)} for d in docs[:3]],
        }
    return state
```

`backend/graph/nodes/reflect.py`:
```python
"""Reflection node — agent reviews the conversation for memorable information."""

from langchain_core.messages import HumanMessage

REFLECT_PROMPT = """Review the conversation above. Extract any information worth remembering long-term:
- User preferences or habits
- Project facts or decisions
- Successful tool usage patterns
- Key dates or names

Respond with a JSON object: {"memories": ["memory 1", "memory 2", ...]}
If nothing is worth remembering, respond with: {"memories": []}
"""


async def reflect_node(state: dict) -> dict:
    """Ask LLM to reflect on conversation and extract memories."""
    llm = state["llm"]
    messages = list(state["messages"])
    messages.append(HumanMessage(content=REFLECT_PROMPT))

    response = await llm.ainvoke(messages)
    return {**state, "reflection": response.content}
```

`backend/graph/nodes/memory_flush.py`:
```python
"""Memory flush node — writes reflection results to Daily Log."""

import json
from datetime import date
from pathlib import Path

import json_repair


async def memory_flush_node(state: dict) -> dict:
    """Parse reflection output and append to daily log."""
    reflection = state.get("reflection", "")
    memory_dir = state.get("memory_dir")
    if not reflection or not memory_dir:
        return state

    try:
        parsed = json.loads(json_repair.repair_json(reflection))
        memories = parsed.get("memories", [])
    except Exception:
        memories = []

    if memories:
        log_path = Path(memory_dir) / "logs" / f"{date.today().isoformat()}.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"- {m}" for m in memories]
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    return {**state, "flushed_memories": memories}
```

**Step 2: Implement langgraph_engine.py**

```python
# backend/graph/engines/langgraph_engine.py
"""LangGraph StateGraph agent engine — the teaching core."""

from __future__ import annotations

from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import START, END, StateGraph
from typing_extensions import TypedDict, Annotated
import operator

from graph.engines.base import BaseEngine, AgentEvent
from graph.nodes.reason import reason_node
from graph.nodes.act import act_node
from graph.nodes.retrieve import retrieve_node
from graph.nodes.reflect import reflect_node
from graph.nodes.memory_flush import memory_flush_node

MAX_ITERATIONS = 20


class AgentState(TypedDict):
    messages: list
    llm: Any
    tools: list
    retriever: Any
    memory_dir: str
    last_response: Any
    reflection: str
    retrieval_results: list
    flushed_memories: list
    iteration: int


def should_continue(state: AgentState) -> str:
    """Route: if last response has tool_calls → 'act', else → 'reflect'."""
    last = state.get("last_response")
    if last and hasattr(last, "tool_calls") and last.tool_calls:
        if state.get("iteration", 0) < MAX_ITERATIONS:
            return "act"
    return "reflect"


class LangGraphEngine(BaseEngine):
    def __init__(self, llm, tools, retriever=None, memory_dir: str = ""):
        self.llm = llm
        self.tools = tools
        self.retriever = retriever
        self.memory_dir = memory_dir
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("retrieve", retrieve_node)
        builder.add_node("reason", reason_node)
        builder.add_node("act", act_node)
        builder.add_node("reflect", reflect_node)
        builder.add_node("memory_flush", memory_flush_node)

        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "reason")
        builder.add_conditional_edges("reason", should_continue, {"act": "act", "reflect": "reflect"})
        builder.add_edge("act", "reason")
        builder.add_edge("reflect", "memory_flush")
        builder.add_edge("memory_flush", END)

        return builder.compile()

    async def astream(
        self,
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> AsyncIterator[AgentEvent]:
        # Convert history dicts to LangChain messages
        messages = [SystemMessage(content=system_prompt)]
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=message))

        initial_state: AgentState = {
            "messages": messages,
            "llm": self.llm,
            "tools": self.tools,
            "retriever": self.retriever,
            "memory_dir": self.memory_dir,
            "last_response": None,
            "reflection": "",
            "retrieval_results": [],
            "flushed_memories": [],
            "iteration": 0,
        }

        # Stream graph execution
        final_content = ""
        async for event in self.graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                if node_name == "retrieve" and node_output.get("retrieval_results"):
                    yield AgentEvent(type="retrieval", data={
                        "results": node_output["retrieval_results"]
                    })

                if node_name == "reason":
                    last = node_output.get("last_response")
                    if last:
                        content = last.content if hasattr(last, "content") else ""
                        if content:
                            yield AgentEvent(type="token", data={"content": content})
                            final_content = content
                        if hasattr(last, "tool_calls") and last.tool_calls:
                            for tc in last.tool_calls:
                                yield AgentEvent(type="tool_start", data={
                                    "tool": tc["name"], "input": tc["args"]
                                })

                if node_name == "act":
                    # Tool results are in the messages
                    msgs = node_output.get("messages", [])
                    from langchain_core.messages import ToolMessage
                    for m in msgs:
                        if isinstance(m, ToolMessage):
                            yield AgentEvent(type="tool_end", data={
                                "tool": "tool", "output": m.content
                            })
                    yield AgentEvent(type="new_response", data={})

        yield AgentEvent(type="done", data={"content": final_content})
```

**Step 3: Write test**

```python
# backend/tests/test_langgraph_engine.py
def test_langgraph_engine_builds_graph():
    from graph.engines.langgraph_engine import LangGraphEngine, AgentState
    # Just verify the graph compiles without errors
    # Actual LLM calls tested in integration tests
    class MockLLM:
        pass
    engine = LangGraphEngine(llm=MockLLM(), tools=[], memory_dir="")
    assert engine.graph is not None


def test_should_continue_no_tool_calls():
    from graph.engines.langgraph_engine import should_continue
    state = {"last_response": None, "iteration": 0}
    assert should_continue(state) == "reflect"


def test_should_continue_with_tool_calls():
    from graph.engines.langgraph_engine import should_continue
    from unittest.mock import Mock
    mock_response = Mock()
    mock_response.tool_calls = [{"name": "test", "args": {}}]
    state = {"last_response": mock_response, "iteration": 0}
    assert should_continue(state) == "act"
```

**Step 4: Run tests, commit**

```bash
cd backend && pytest tests/test_langgraph_engine.py -v
git add backend/graph/nodes/ backend/graph/engines/langgraph_engine.py backend/tests/test_langgraph_engine.py
git commit -m "feat: LangGraph state machine engine with retrieve/reason/act/reflect/flush nodes"
```

---

### Task 10: create_agent Engine

**Files:**
- Create: `backend/graph/engines/create_agent_engine.py`
- Test: `backend/tests/test_create_agent_engine.py`

**Step 1: Implement**

```python
# backend/graph/engines/create_agent_engine.py
"""LangChain v1 create_agent wrapper engine."""

from __future__ import annotations

from typing import AsyncIterator

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from graph.engines.base import BaseEngine, AgentEvent


class CreateAgentEngine(BaseEngine):
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    async def astream(
        self,
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> AsyncIterator[AgentEvent]:
        agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
        )

        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=message))

        final_content = ""
        async for event in agent.astream({"messages": messages}):
            # Normalize LangChain events to our AgentEvent format
            if isinstance(event, dict):
                for key, value in event.items():
                    if key == "agent":
                        msgs = value.get("messages", [])
                        for m in msgs:
                            if hasattr(m, "content") and m.content:
                                yield AgentEvent(type="token", data={"content": m.content})
                                final_content = m.content
                            if hasattr(m, "tool_calls") and m.tool_calls:
                                for tc in m.tool_calls:
                                    yield AgentEvent(type="tool_start", data={
                                        "tool": tc["name"], "input": tc.get("args", {})
                                    })
                    elif key == "tools":
                        msgs = value.get("messages", [])
                        for m in msgs:
                            yield AgentEvent(type="tool_end", data={
                                "tool": "tool", "output": getattr(m, "content", "")
                            })
                        yield AgentEvent(type="new_response", data={})

        yield AgentEvent(type="done", data={"content": final_content})
```

**Step 2: Write test, run, commit**

```python
# backend/tests/test_create_agent_engine.py
def test_create_agent_engine_init():
    from graph.engines.create_agent_engine import CreateAgentEngine
    class MockLLM:
        pass
    engine = CreateAgentEngine(llm=MockLLM(), tools=[])
    assert engine.llm is not None
```

```bash
cd backend && pytest tests/test_create_agent_engine.py -v
git add backend/graph/engines/create_agent_engine.py backend/tests/
git commit -m "feat: create_agent engine wrapping LangChain v1 API"
```

---

### Task 11: AgentManager (Unified Entry Point)

**Files:**
- Create: `backend/graph/agent.py`
- Test: `backend/tests/test_agent_manager.py`

**Step 1: Implement**

```python
# backend/graph/agent.py
"""AgentManager — unified entry point that switches between engines."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator

from config import AppConfig, load_config
from graph.engines.base import BaseEngine, AgentEvent
from graph.prompt_builder import PromptBuilder
from graph.session_manager import SessionManager
from providers.registry import get_llm, get_embeddings
from tools import get_all_tools
from tools.skills_scanner import write_snapshot


class AgentManager:
    def __init__(self, base_dir: str | Path, config: AppConfig | None = None):
        self.base_dir = Path(base_dir).resolve()
        self.config = config or load_config()
        self.llm = None
        self.tools = []
        self.session_manager = SessionManager(self.base_dir / "sessions")
        self.prompt_builder = PromptBuilder(self.base_dir)

    def initialize(self):
        """Called at startup — build LLM, tools, scan skills."""
        write_snapshot(self.base_dir)
        self.llm = get_llm(self.config)
        self.tools = get_all_tools(self.base_dir)

    def _get_engine(self) -> BaseEngine:
        engine_name = self.config.agent_engine

        if engine_name == "langgraph":
            from graph.engines.langgraph_engine import LangGraphEngine
            return LangGraphEngine(
                llm=self.llm,
                tools=self.tools,
                memory_dir=str(self.base_dir / "memory"),
            )
        elif engine_name == "create_agent":
            from graph.engines.create_agent_engine import CreateAgentEngine
            return CreateAgentEngine(llm=self.llm, tools=self.tools)
        elif engine_name == "raw_loop":
            from graph.engines.raw_loop_engine import RawLoopEngine
            # Build OpenAI-format tool schemas from LangChain tools
            tool_schemas = [_lc_tool_to_openai_schema(t) for t in self.tools]
            tool_executor = {t.name: t.ainvoke for t in self.tools}
            return RawLoopEngine(
                api_base=self._get_api_base(),
                api_key=self._get_api_key(),
                model=self.config.llm.model,
                tools=tool_schemas,
                tool_executor=tool_executor,
            )
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

    async def astream(self, message: str, session_id: str) -> AsyncIterator[AgentEvent]:
        history = self.session_manager.load_session_for_agent(session_id)
        system_prompt = self.prompt_builder.build(rag_mode=self.config.rag_mode)
        engine = self._get_engine()

        async for event in engine.astream(message, history, system_prompt):
            yield event

    def _get_api_base(self) -> str:
        from providers.registry import get_provider_spec
        spec = get_provider_spec(self.config.llm.provider)
        creds = self.config.providers.get(self.config.llm.provider)
        return (creds.api_base if creds and creds.api_base else "") or (spec.api_base_default if spec else "")

    def _get_api_key(self) -> str:
        import os
        from providers.registry import get_provider_spec
        spec = get_provider_spec(self.config.llm.provider)
        if spec and spec.env_key:
            return os.getenv(spec.env_key, "")
        return ""


def _lc_tool_to_openai_schema(tool) -> dict:
    """Convert LangChain tool to OpenAI function-calling schema."""
    schema = tool.args_schema.schema() if hasattr(tool, "args_schema") and tool.args_schema else {}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }
```

**Step 2: Test and commit**

```python
# backend/tests/test_agent_manager.py
import tempfile
from pathlib import Path


def test_agent_manager_init():
    from graph.agent import AgentManager
    from config import AppConfig
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        # Create minimal workspace
        for d in ["workspace", "memory", "memory/logs", "skills", "sessions", "knowledge", "storage"]:
            (base / d).mkdir(parents=True, exist_ok=True)
        (base / "workspace" / "SOUL.md").write_text("soul")
        (base / "workspace" / "IDENTITY.md").write_text("id")
        (base / "workspace" / "USER.md").write_text("user")
        (base / "workspace" / "AGENTS.md").write_text("agents")
        (base / "memory" / "MEMORY.md").write_text("mem")

        cfg = AppConfig()
        am = AgentManager(base_dir=td, config=cfg)
        assert am.session_manager is not None
        assert am.config.agent_engine == "langgraph"
```

```bash
cd backend && pytest tests/test_agent_manager.py -v
git add backend/graph/agent.py backend/tests/test_agent_manager.py
git commit -m "feat: AgentManager with engine switching and unified streaming"
```

---

## Phase 5: Memory System

### Task 12: Native Memory Backend (Daily Logs + MEMORY.md)

**Files:**
- Create: `backend/memory/base.py`
- Create: `backend/memory/native/daily_log.py`
- Create: `backend/memory/native/knowledge.py`
- Create: `backend/memory/native/flush.py`
- Test: `backend/tests/test_memory_native.py`

**Implementation:** See design doc section 4. The `MemoryBackend` ABC defines `add_memory`, `search_memory`, `get_all`, `flush`. `NativeMemoryBackend` writes to `memory/logs/YYYY-MM-DD.md` (Layer 1) and `memory/MEMORY.md` (Layer 2). `flush()` calls LLM to distill Daily Logs into MEMORY.md.

**Step 1: Implement base.py**

```python
# backend/memory/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MemoryItem:
    content: str
    score: float = 0.0
    source: str = ""


class MemoryBackend(ABC):
    @abstractmethod
    async def add_memory(self, content: str, metadata: dict | None = None) -> None: ...

    @abstractmethod
    async def search_memory(self, query: str, top_k: int = 5) -> list[MemoryItem]: ...

    @abstractmethod
    async def get_all(self) -> str: ...

    @abstractmethod
    async def flush(self) -> None: ...
```

**Step 2:** Implement `daily_log.py`, `knowledge.py`, `flush.py` following the Daily Logs append-only pattern and MEMORY.md structured sections. Write tests. Commit.

```bash
git commit -m "feat: native dual-layer memory backend with daily logs and flush"
```

---

### Task 13: Memory Indexer (Hybrid Retrieval)

**Files:**
- Create: `backend/graph/memory_indexer.py`
- Test: `backend/tests/test_memory_indexer.py`

**Implementation:** Uses `langchain_milvus.Milvus` for vector store, `langchain_community.retrievers.BM25Retriever` for keyword search, `langchain.retrievers.EnsembleRetriever` for hybrid (weights=[0.7, 0.3]). Indexes both `memory/MEMORY.md` and files in `knowledge/`. `rebuild_index()` re-reads files, chunks with `RecursiveCharacterTextSplitter(chunk_size=256, chunk_overlap=32)`, and rebuilds.

```bash
git commit -m "feat: memory indexer with Milvus + BM25 hybrid retrieval"
```

---

### Task 14: Mem0 Backend

**Files:**
- Create: `backend/memory/mem0_backend.py`
- Test: `backend/tests/test_mem0_backend.py`

**Implementation:** Wraps `mem0.Memory` with the `MemoryBackend` interface. Config-driven initialization. `add_memory` calls `memory.add()`, `search_memory` calls `memory.search()`.

```bash
git commit -m "feat: Mem0 alternate memory backend"
```

---

## Phase 6: API Layer

### Task 15: FastAPI App + Chat SSE Endpoint

**Files:**
- Modify: `backend/app.py`
- Create: `backend/api/chat.py`
- Test: `backend/tests/test_api_chat.py`

**Implementation:** Wire up `AgentManager` in lifespan. `POST /api/chat` accepts `{message, session_id, stream}`, calls `agent_manager.astream()`, yields SSE events. Uses `starlette.responses.StreamingResponse` with `text/event-stream` content type. After `done` event, save user message + assistant segments to session.

```bash
git commit -m "feat: SSE streaming chat endpoint"
```

---

### Task 16: Sessions + Files + Skills APIs

**Files:**
- Create: `backend/api/sessions.py`
- Create: `backend/api/files.py`
- Test: `backend/tests/test_api_sessions.py`

**Implementation:** CRUD endpoints for sessions (list, create, rename, delete, get messages, get history, generate title). File endpoints with path whitelist (`workspace/`, `memory/`, `skills/`, `knowledge/`, `SKILLS_SNAPSHOT.md`) + traversal protection. Skills listing endpoint.

```bash
git commit -m "feat: session management and file operations APIs"
```

---

### Task 17: Tokens + Compress + Config APIs

**Files:**
- Create: `backend/api/tokens.py`
- Create: `backend/api/compress.py`
- Create: `backend/api/config_api.py`
- Modify: `backend/app.py` (register all routers)

**Implementation:** Token counting with `tiktoken` `cl100k_base`. Compression: take front 50% messages, LLM summarize, archive. Config APIs: GET/PUT for `rag_mode`, `agent_engine`, `memory_backend`.

```bash
git commit -m "feat: token stats, compression, and config APIs"
```

---

## Phase 7: Frontend

### Task 18: Next.js Scaffold + Layout + Navbar

**Files:**
- Create: `frontend/` (via `npx create-next-app@14`)
- Create: `frontend/src/components/layout/Navbar.tsx`
- Create: `frontend/src/app/globals.css`

**Step 1: Scaffold**

```bash
cd mini-openclaw
npx create-next-app@14 frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias
cd frontend
npx shadcn-ui@latest init
```

**Step 2:** Build Navbar with "mini OpenClaw" on left, GitHub link (https://github.com/hfhfn) on right. Apple frosty glass style. Configure Tailwind with Klein Blue accent color.

```bash
git commit -m "feat: Next.js scaffold with Navbar and Apple glass theme"
```

---

### Task 19: Sidebar + State Management

**Files:**
- Create: `frontend/src/lib/store.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/layout/Sidebar.tsx`

**Implementation:** React Context for global state (sessions, active session, messages, settings). API client with SSE parser for POST. Sidebar: session list, settings panel (engine/memory/RAG toggles), token overview.

```bash
git commit -m "feat: sidebar with session list, settings, and state management"
```

---

### Task 20: ChatPanel + Messages

**Files:**
- Create: `frontend/src/components/chat/ChatPanel.tsx`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/ChatMessage.tsx`
- Create: `frontend/src/components/layout/ResizeHandle.tsx`
- Modify: `frontend/src/app/page.tsx`

**Implementation:** Three-panel layout with draggable resize handles. ChatMessage renders Markdown. ChatInput with send button. Main page assembles Sidebar + ChatPanel + InspectorPanel.

```bash
git commit -m "feat: chat panel with markdown messages and 3-panel layout"
```

---

### Task 21: ThoughtChain + RetrievalCard

**Files:**
- Create: `frontend/src/components/chat/ThoughtChain.tsx`
- Create: `frontend/src/components/chat/RetrievalCard.tsx`

**Implementation:** Collapsible thought chain showing tool_start → tool_end events. Color-coded: RAG=purple, tools=blue, errors=red. RetrievalCard shows RAG results in a purple collapsible card.

```bash
git commit -m "feat: thought chain visualization and RAG retrieval cards"
```

---

### Task 22: InspectorPanel (Monaco Editor + Token Stats)

**Files:**
- Create: `frontend/src/components/editor/InspectorPanel.tsx`

**Step 1: Install Monaco**

```bash
cd frontend && npm install @monaco-editor/react
```

**Step 2:** File tree navigator for workspace/memory/skills. Monaco editor for selected file. Save button triggers POST to `/api/files`. Token stats panel below editor showing system/history/total token counts from `/api/tokens/session/{id}`. Compress button.

```bash
git commit -m "feat: inspector panel with Monaco editor and token statistics"
```

---

## Phase 8: Deployment

### Task 23: Docker + Docker Compose

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`

**Implementation:**

Backend Dockerfile: Python 3.12-slim, install requirements, copy source, uvicorn entrypoint.

Frontend Dockerfile: Node 20-alpine, npm install, npm run build, Next.js standalone output.

docker-compose.yml: backend (port 8002), frontend (port 3000), optional postgres+pgvector via `--profile pgvector`.

```bash
git commit -m "feat: Docker and docker-compose deployment"
```

---

## Verification Checklist

After all tasks are complete, verify:

1. `cd backend && pytest tests/ -v` — all tests pass
2. `cd backend && ruff check .` — no lint errors
3. `cd backend && uvicorn app:app --port 8002` — backend starts
4. `cd frontend && npm run build` — frontend builds
5. `curl http://localhost:8002/api/health` — returns `{"status":"ok"}`
6. Open `http://localhost:3000` — three-panel UI loads
7. Send a chat message — SSE stream works, thought chain visible
8. Switch engines via sidebar — all three engines respond
9. Edit MEMORY.md in Monaco — changes persist
10. `docker compose up` — both services start
