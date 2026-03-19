"""Global configuration with JSON persistence."""

from __future__ import annotations  #允许在类定义中使用尚未定义的类作为类型注解（例如在类内部引用自身），提高类型系统灵活性。

import json
from pathlib import Path
from typing import Literal   #限制变量只能取特定的几个字面值（如字符串常量），常用于配置选项的枚举。

from pydantic import BaseModel, Field  #Pydantic 的核心组件。BaseModel 用于定义数据模型，提供自动验证；Field 用于为字段添加元数据（如默认工厂函数）。

_BASE_DIR = Path(__file__).resolve().parent
_DEFAULT_CONFIG_PATH = _BASE_DIR / "config.json"

# 详细中文注释

class LLMConfig(BaseModel):     #继承自BaseModel，用于定义大模型配置的字段。
    provider: str = "zhipu"
    model: str = "Pro/zai-org/GLM-4.7"
    temperature: float = 0.7
    max_tokens: int = 4096


class EmbeddingConfig(BaseModel):    #继承自BaseModel，用于定义嵌入模型配置的字段。
    provider: str = "siliconflow"  ## 默认嵌入模型供应商（硅基流动）
    model: str = "BAAI/bge-m3"
    api_base: str = "https://api.siliconflow.cn/v1"


class ProviderCreds(BaseModel):  #继承自BaseModel，用于定义供应商 API 密钥和基础 URL 的字段。
    api_key: str = ""   # 供应商 API 密钥
    api_base: str = ""  # 供应商 API 基础 URL


class AppConfig(BaseModel):
    # 智能体运行引擎，可选：原生实现、LangGraph 框架或原始循环逻辑
    agent_engine: Literal["create_agent", "langgraph", "raw_loop"] = "langgraph"  # 智能体运行引擎，默认使用 LangGraph 框架
    # 记忆系统后端，可选：原生文件系统存储或 Mem0 专业记忆管理
    memory_backend: Literal["native", "mem0"] = "native"
    # 向量数据库类型，用于 RAG 或长期记忆检索，可选：Milvus、PGVector 或 FAISS
    vector_store: Literal["milvus", "pgvector", "faiss"] = "milvus"
    # 是否启用 RAG 模式
    rag_mode: bool = False
    # 嵌套子模型，使用 Field 的 default_factory 确保每个实例都有独立的默认对象
    llm: LLMConfig = Field(default_factory=LLMConfig)
    # 嵌入模型配置，默认工厂函数创建独立实例
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    # 供应商 API 密钥映射，键为供应商名称
    providers: dict[str, ProviderCreds] = Field(default_factory=dict)


def load_config(path: Path = _DEFAULT_CONFIG_PATH) -> AppConfig:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))    #如果 json对应值和类中的默认不同，会如何？会覆盖默认值
        return AppConfig.model_validate(data)    #model_validate有什么用？ 
    return AppConfig()


def save_config(cfg: AppConfig, path: Path = _DEFAULT_CONFIG_PATH) -> None:
    path.write_text(
        cfg.model_dump_json(indent=2),
        encoding="utf-8",
    )


# Singleton — imported by other modules 单例是否只加载一次
config = load_config()
"""
    单例模式: 这一行在模块加载时立即执行 load_config()。由于 Python 模块导入的特性，其他模块（如 app.py 或 agent.py）通过 from backend.config import config 
    导入的将是同一个 AppConfig 实例。这种做法保证了配置在内存中的唯一性，修改 config 的属性后调用 save_config(config) 即可同步更新磁盘文件。
"""