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
        display_name="\u667a\u8c31 GLM",
        default_model="glm-4.7-flash",
        api_base_default="https://open.bigmodel.cn/api/paas/v4",
        manages_own_base=True,
        api_key_alias="zhipuai_api_key",
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
        display_name="Ollama (\u672c\u5730)",
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
    }

    # API key — resolve from env or config
    api_key = None
    if spec.env_key:
        api_key = os.getenv(spec.env_key) or cfg.providers.get(spec.name, None)
        if api_key and hasattr(api_key, "api_key"):
            api_key = api_key.api_key

    # Provider-specific key param names (e.g. ChatZhipuAI uses zhipuai_api_key)
    if isinstance(api_key, str) and api_key:
        key_param = spec.api_key_alias or "api_key"
        kwargs[key_param] = api_key

    # API base — some SDKs manage their own endpoint (e.g. ChatZhipuAI)
    if not spec.manages_own_base:
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
