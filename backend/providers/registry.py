"""Provider registry — single source of truth for all LLM/Embedding providers."""

from __future__ import annotations

import importlib  # 核心库：用于在运行时动态导入 Python 模块
import os         # 用于读取操作系统环境变量（API Key）
from typing import Any # 用于表示可以是任何类型的变量

# 从 LangChain 导入基础类，用于类型限定（确保返回的对象符合 LangChain 标准）
from langchain_core.language_models import BaseChatModel # 聊天模型基类
from langchain_core.embeddings import Embeddings          # 嵌入模型基类

from providers.base import ProviderSpec
from config import config, AppConfig

PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="zhipu",
        llm_class="langchain_openai.ChatOpenAI",
        env_key="ZHIPUAI_API_KEY",
        display_name="\u667a\u8c31 GLM",
        default_model="Pro/zai-org/GLM-4.7",
        api_base_default="https://api.siliconflow.cn/v1",
        manages_own_base=False,
        api_key_alias="",   # API Key 的参数别名（某些 SDK 可能不叫 api_key）
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
        llm_class="langchain_ollama.ChatOllama",  # Ollama 使用专门的 LangChain 库
        env_key=None,                             # 本地运行通常不需要 Key
        display_name="Ollama (\u672c\u5730)",
        default_model="qwen2.5:7b",
        supports_embedding=True,                  # 标记该供应商支持向量嵌入
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
    """输入供应商名称，返回其配置规格对象。如果不存在则返回 None"""
    return next((p for p in PROVIDERS if p.name == name), None)


def _resolve_class(dotted_path: str) -> type:
    """
    将字符串（如 "langchain_openai.ChatOpenAI"）变成可以被调用的类
    输入: 类的全路径字符串 (例如 "a.b.C")
    输出: 真实的 Python 类对象 (type)
    """
    # 1. 将路径按最后一个点拆分为：模块路径 "a.b" 和 类名 "C"
    module_path, class_name = dotted_path.rsplit(".", 1)
    # 2. 使用 importlib 动态加载该模块。这相当于执行了 `import a.b`
    # 这样可以避免在文件顶部写死所有 import，减少启动负担
    module = importlib.import_module(module_path)
    # 3. 从模块对象中获取对应的类属性并返回
    return getattr(module, class_name)


def get_llm(cfg: AppConfig | None = None) -> BaseChatModel:
    """
    输入: 可选的 AppConfig 对象（如果不传则使用全局单例 config）
    返回: BaseChatModel 实例（这是 LangChain 要求的标准返回类型，支持 .ainvoke()）
    """
    # 1. 确定配置源
    cfg = cfg or config
    spec = get_provider_spec(cfg.llm.provider)
    if spec is None:
        raise ValueError(f"Unknown LLM provider: {cfg.llm.provider}")
    # 3. 动态加载 LangChain 类（如 ChatOpenAI）
    cls = _resolve_class(spec.llm_class)
    
    # 4. 准备构造函数的参数字典 (kwargs)
    kwargs: dict[str, Any] = {
        "model": cfg.llm.model or spec.default_model,  # 优先使用用户配置的模型，否则用默认值
        "temperature": cfg.llm.temperature,            # 生成温度
        "max_tokens": cfg.llm.max_tokens,              # 最大长度限制
    }

    # 5. 解析 API Key
    # API key — resolve from env or config
    api_key = None
    if spec.env_key:
        # 优先级：环境变量 > 内存配置
        api_key = os.getenv(spec.env_key) or cfg.providers.get(spec.name, None)
        # 如果配置存的是对象，提取其 api_key 属性
        if api_key and hasattr(api_key, "api_key"):    #需要详细分析
            api_key = api_key.api_key

    # 6. 处理 API Key 的参数名称注入
    # Provider-specific key param names (e.g. ChatZhipuAI uses zhipuai_api_key)
    if isinstance(api_key, str) and api_key:
        # 某些 SDK 要求参数名为 zhipuai_api_key，这里通过 alias 处理
        key_param = spec.api_key_alias or "api_key"
        kwargs[key_param] = api_key

    # 7. 处理 API 基础地址 (Base URL)
    # API base — some SDKs manage their own endpoint (e.g. ChatZhipuAI)
    if not spec.manages_own_base:
        creds = cfg.providers.get(spec.name)
        # 优先级：配置项中的 api_base > 供应商默认地址
        api_base = (creds.api_base if creds and creds.api_base else "") or spec.api_base_default
        if api_base:
            kwargs["base_url"] = api_base
    #kwargs的详细参数：
    # model: 模型名称，如 "gpt-4o"
    # temperature: 生成温度，0-2 之间，默认 0.7
    # max_tokens: 最大生成 token 数，默认 1024
    # api_key: API 密钥，根据供应商不同有不同参数名（如 zhipuai_api_key）
    # base_url: API 基础地址，如 "https://api.siliconflow.cn/v1"
    return cls(**kwargs)


def get_embeddings(cfg: AppConfig | None = None) -> Embeddings:
    
    """
    输入: AppConfig
    返回: Embeddings 实例 (符合 LangChain 嵌入标准)
    """
    cfg = cfg or config
    emb_cfg = cfg.embedding

    # 特殊处理：SiliconFlow 虽然兼容 OpenAI 格式，但逻辑通常比较固定
    # SiliconFlow uses OpenAI-compatible endpoint
    if emb_cfg.provider == "siliconflow":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=emb_cfg.model,
            openai_api_key=os.getenv("SILICONFLOW_API_KEY", ""),
            openai_api_base=emb_cfg.api_base,
        )

    # 通用处理逻辑
    spec = get_provider_spec(emb_cfg.provider)
    if spec and spec.embedding_class:
        
        # 动态解析嵌入类
        cls = _resolve_class(spec.embedding_class)
        kwargs = {"model": emb_cfg.model}
        if emb_cfg.api_base:
            kwargs["base_url"] = emb_cfg.api_base
        return cls(**kwargs)

    raise ValueError(f"No embedding support for provider: {emb_cfg.provider}")
