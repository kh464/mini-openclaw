# backend/graph/agent.py
"""AgentManager — unified entry point that switches between engines."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator

from config import AppConfig, load_config
from graph.engines.base import BaseEngine, AgentEvent
from graph.prompt_builder import PromptBuilder
from graph.session_manager import SessionManager
from providers.registry import get_llm
from tools import get_all_tools
from tools.skills_scanner import write_snapshot


class AgentManager:
    
    
    def __init__(self, base_dir: str | Path, config: AppConfig | None = None):
        """
        构造函数：初始化管理器的基本骨架。
        :param base_dir: 项目根目录，用于定位 sessions、skills 和 workspace。
        :param config: 全局配置对象。如果为 None，则从磁盘加载默认配置。
        """
        
        self.base_dir = Path(base_dir).resolve() # 确保路径为绝对路径
        self.config = config or load_config()    # 如果没传配置，则加载默认配置
        self.llm = None                          # 初始化时 LLM 为空，待 initialize 调用
        self.tools = []                          # 初始化时工具列表为空
        self.session_manager = SessionManager(self.base_dir / "sessions") # 会话管理  需要详细阅读
        self.prompt_builder = PromptBuilder(self.base_dir)                # 提示词构建  需要详细阅读

    def initialize(self):    #整个程序生命周期只调用一次，用于初始化 LLM、工具、扫描技能等
        """
        启动初始化：这是“重型”任务区，只在服务启动时运行一次。
        1. 扫描 skills 文件夹，生成最新的能力快照文件。
        2. 根据配置（如 zhipu, openai）实例化 LLM。
        3. 加载所有 Python 编写的工具（如 fetch_url, python_repl）。
        """
        """Called at startup — build LLM, tools, scan skills."""
        write_snapshot(self.base_dir)        # 扫描当前的技能（Skills）并写入快照
        self.llm = get_llm(self.config)      # 根据配置获取 LLM 实例（如智谱、OpenAI 等）
        self.tools = get_all_tools(self.base_dir) # 加载所有可用的工具（Weather, Python REPL 等）

    def _get_engine(self) -> BaseEngine:    #根据配置返回不同的引擎（如 LangGraph、CreateAgent、RawLoop 等）
        #背景：AI 领域发展极快。今天可能流行 LangGraph（图编排），明天可能流行简单的 ReAct 循环。
        """工业价值：通过这个方法，开发者可以在不改动核心业务代码（如 app.py 或 api/chat.py）的情况下，
        通过修改 config.json 里的一个字符串，就彻底更换整个 AI 的运行逻辑。"""
        engine_name = self.config.agent_engine

        if engine_name == "langgraph":
            """
            A. LangGraph 引擎 (langgraph)
            这是目前最强大的模式，适合处理复杂的、有状态的任务流。

            特点：将任务看作一个“图”，有节点（推理、行动）和边（跳转逻辑）。

            注入参数：

            llm: 刚才初始化的模型实例。

            tools: 所有的工具。

            memory_dir: 传递了 memory/ 路径，用于实现长期记忆（持久化状态）。
            """
            from graph.engines.langgraph_engine import LangGraphEngine
            return LangGraphEngine(      #需要详细阅读 LangGraphEngine 类的文档
                llm=self.llm,
                tools=self.tools,
                memory_dir=str(self.base_dir / "memory"),
            )
        elif engine_name == "create_agent":
            """
            B. 标准 Agent 引擎 (create_agent)
            这是 LangChain 官方推荐的标准 ReAct 模式。

            特点：逻辑相对固定，适合标准的“思考-行动-观察”循环。

            优势：开发速度快，代码简洁。
            """
            from graph.engines.create_agent_engine import CreateAgentEngine
            return CreateAgentEngine(llm=self.llm, tools=self.tools)    #需要详细阅读 CreateAgentEngine 类的文档
        elif engine_name == "raw_loop":
            """
            这是本项目中最能体现底层控制力的部分。它绕过了 LangChain 的 Agent 封装，直接手动写 HTTP 请求循环。

                协议转换：这里调用了 _lc_tool_to_openai_schema，将工具翻译成模型能听懂的 JSON。

                执行器解耦：构造了一个 tool_executor 字典，直接把工具的 ainvoke 方法传进去。

                动态配置：它不使用已经初始化的 self.llm，而是直接从 config 中读取 API Key 和 Base URL。
                这意味着它具备**“热刷新”**能力（改了配置立即生效）。
            """
            from graph.engines.raw_loop_engine import RawLoopEngine
            # Build OpenAI-format tool schemas from LangChain tools
            tool_schemas = [_lc_tool_to_openai_schema(t) for t in self.tools]
            tool_executor = {t.name: t.ainvoke for t in self.tools}
            return RawLoopEngine(      #需要详细阅读 RawLoopEngine 类的文档
                api_base=self._get_api_base(),
                api_key=self._get_api_key(),
                model=self.config.llm.model,
                tools=tool_schemas,
                tool_executor=tool_executor,
            )
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

    async def astream(self, message: str, session_id: str) -> AsyncIterator[AgentEvent]:
        """
        详细讲解 astream：
        该方法实现了“请求上下文增强”的核心逻辑。
        
        1. 加载历史：根据 session_id 从磁盘加载 JSON 格式的历史对话，
           确保智能体拥有“短期记忆”。
           
        2. 构建环境：调用 PromptBuilder 拼接 SOUL, IDENTITY, SKILLS_SNAPSHOT 等文件，
           构建环境：调用 PromptBuilder 拼接 SOUL, IDENTITY, SKILLS_SNAPSHOT 等文件，
           
        3. 引擎适配：调用 _get_engine()。这体现了工业级的策略模式，
           无论底层是用 LangGraph 还是原生循环，对外界暴露的都是统一的 astream 接口。
           
        4. 流式转发：通过 async for 实时获取引擎产生的事件（如 Token、工具调用），
           并将其 yield（产出）给前端 API 层。
        """
        history = self.session_manager.load_session_for_agent(session_id)
        system_prompt = self.prompt_builder.build(rag_mode=self.config.rag_mode)
        engine = self._get_engine()
        #这里的astream和上面的astream方法是不同的，这里的astream是异步的，而上面的astream是同步的
        async for event in engine.astream(message, history, system_prompt):  #astream 方法返回一个异步迭代器，用于流式产出事件
            yield event   # 逐条产出事件，前端可以实时接收

    def _get_api_base(self) -> str:    #根据配置返回 API Base URL
        from providers.registry import get_provider_spec
        spec = get_provider_spec(self.config.llm.provider)
        creds = self.config.providers.get(self.config.llm.provider)
        return (creds.api_base if creds and creds.api_base else "") or (spec.api_base_default if spec else "")

    def _get_api_key(self) -> str:    #根据配置返回 API Key
        import os
        from providers.registry import get_provider_spec
        spec = get_provider_spec(self.config.llm.provider)
        if spec and spec.env_key:
            return os.getenv(spec.env_key, "")
        return ""


def _lc_tool_to_openai_schema(tool) -> dict:    #将 LangChain 工具对象转换为 OpenAI 格式的的 JSON Schema
    """
    详细讲解协议转换：
    
    1. 背景：LangChain 工具对象包含丰富的元数据（name, description, args_schema）。
    例如fetch_url_tool.py
    class FetchUrlInput(BaseModel):
        url: str = Field(description="要获取内容的 URL 地址")

    class FetchUrlTool(BaseTool):
        name = "fetch_url"
        args_schema: Type[BaseModel] = FetchUrlInput # 绑定说明书
    2. 动作：
       - 利用 Pydantic 的 model_json_schema() 自动将参数定义转化为标准的 JSON Schema。
       - 构造 OpenAI 要求的 function 定义格式。
    3. 目的：让大模型知道这个工具有哪些参数、必填项是什么，从而精确生成 tool_calls。
    """
    """Convert LangChain tool to OpenAI function-calling schema."""
    schema = tool.args_schema.model_json_schema() if hasattr(tool, "args_schema") and tool.args_schema else {}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }
