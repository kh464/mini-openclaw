# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**nanobot** is an ultra-lightweight personal AI assistant (~4,000 lines of core agent code) inspired by OpenClaw. The main source code lives in the `nanobot/` subdirectory (which is also a standalone Python package). Python 3.11+ required.

## Common Commands

All commands should be run from the `nanobot/` subdirectory.

### Install (development)
```bash
cd nanobot
pip install -e .
```

### Run
```bash
nanobot onboard           # Initialize config & workspace
nanobot agent             # Interactive chat mode
nanobot agent -m "..."    # Single message mode
nanobot gateway           # Start chat channel gateway
nanobot status            # Show system status
```

### Test
```bash
cd nanobot
pytest tests/                        # Run all tests
pytest tests/test_commands.py        # Run a single test file
pytest tests/test_commands.py -k "test_onboard_fresh"  # Run a single test
```
Tests use `pytest` with `pytest-asyncio` (asyncio_mode = "auto"). Test directory: `nanobot/tests/`.

### Lint
```bash
cd nanobot
ruff check nanobot/       # Lint
ruff format nanobot/      # Format
```
Ruff config: line-length 100, target Python 3.11, rules E/F/I/N/W, E501 ignored.

### Docker
```bash
cd nanobot
docker build -t nanobot .
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot agent -m "Hello!"
```

### Verify core line count
```bash
cd nanobot
bash core_agent_lines.sh
```

## Architecture

### Processing Flow
```
InboundMessage → MessageBus → AgentLoop → LLM call → Tool execution → OutboundMessage
```

The **AgentLoop** (`nanobot/nanobot/agent/loop.py`) is the central engine. Each iteration: receive message → build context (system prompt + history + memory + skills) → call LLM → parse/execute tool calls → send response. Max 20 iterations per turn by default.

### Key Modules

| Module | Path | Role |
|--------|------|------|
| **AgentLoop** | `agent/loop.py` | Core loop: LLM calls, tool dispatch, streaming |
| **ContextBuilder** | `agent/context.py` | Assembles system prompt from bootstrap files (AGENTS.md, SOUL.md, USER.md, TOOLS.md), memory, skills |
| **ToolRegistry** | `agent/tools/registry.py` | Dynamic tool registration, schema for LLM |
| **Tool base** | `agent/tools/base.py` | Base class with `name`, `description`, `parameters` (JSON schema), `execute()` |
| **MemoryStore** | `agent/memory.py` | Persistent memory via `workspace/memory/MEMORY.md` |
| **SkillsLoader** | `agent/skills.py` | Scans skills dirs, loads SKILL.md with YAML frontmatter |
| **SubagentManager** | `agent/subagent.py` | Spawns background tasks with independent context |
| **SessionManager** | `session/manager.py` | Conversation sessions with history window (default 50) |
| **MessageBus** | `bus/queue.py` | Routes InboundMessage/OutboundMessage between channels and agent |
| **ChannelManager** | `channels/manager.py` | Orchestrates all chat integrations |
| **ProviderRegistry** | `providers/registry.py` | Single source of truth for LLM providers (PROVIDERS constant) |
| **Config** | `config/schema.py` + `config/loader.py` | Pydantic v2 config from `~/.nanobot/config.json` |
| **CronService** | `cron/service.py` | Scheduled task execution |
| **HeartbeatService** | `heartbeat/service.py` | Checks HEARTBEAT.md every 30 min, spawns tasks |

All paths above are relative to `nanobot/nanobot/`.

### Built-in Tools
`filesystem.py` (read/write/edit/list_dir), `shell.py` (exec), `web.py` (search/fetch), `message.py`, `spawn.py`, `cron.py`, `mcp.py`. All extend `Tool` base class in `tools/base.py`.

### Chat Channels
Each in `channels/`: telegram, discord, whatsapp, feishu, dingtalk, slack, email, qq, mochat. All extend `BaseChannel`. WhatsApp requires a separate Node.js bridge (`nanobot/bridge/`).

### LLM Providers
Adding a new provider takes 2 steps:
1. Add `ProviderSpec` to `PROVIDERS` in `providers/registry.py`
2. Add field to `ProvidersConfig` in `config/schema.py`

Most providers use LiteLLM. Special cases: `custom_provider.py` (direct OpenAI-compatible), `openai_codex_provider.py` (OAuth).

### Skills System
Skills are directories containing a `SKILL.md` with YAML frontmatter. Built-in skills: `nanobot/nanobot/skills/`. User skills: `~/.nanobot/skills/`. Skills are lazy-loaded — only their summaries appear in context until invoked.

### MCP Integration
MCP servers configured in `config.json` under `tools.mcpServers`. Supports stdio (command+args) and HTTP (url) transports. Tools auto-discovered and registered alongside built-in tools.

### Configuration
Config lives at `~/.nanobot/config.json`. Pydantic v2 schema in `config/schema.py`. Supports both camelCase and snake_case keys. Workspace files at `~/.nanobot/workspace/` (AGENTS.md, SOUL.md, USER.md, TOOLS.md, HEARTBEAT.md, memory/).

## Build System

Uses **hatchling** (PEP 517). Package published to PyPI as `nanobot-ai`. Non-Python files (skills `.md`/`.sh`) are included via hatch build config. The WhatsApp bridge is force-included in the wheel.
