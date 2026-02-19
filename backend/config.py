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
    model: str = "glm-4.7-flash"
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
