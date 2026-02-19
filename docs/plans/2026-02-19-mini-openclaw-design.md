# Mini-OpenClaw 系统设计文档

## 1. 项目概述

基于 OpenClaw/nanobot 的教学研究项目，从头构建一个全栈 AI Agent 系统。核心目标：学习 Agent 系统的完整工程实现，通过三套引擎对比和可视化特性支持教学。

**技术栈**：
- 后端：Python 3.10+ / FastAPI / LangChain 1.x / LangGraph
- 前端：Next.js 14 App Router / TypeScript / Shadcn/UI / Monaco Editor
- 向量数据库：Milvus Lite (默认) / pgvector (可选)
- 默认 LLM：GLM-4-Flash (智谱)
- 默认 Embedding：BAAI/bge-m3 (SiliconFlow)

---

## 2. 整体架构

### 目录结构

```
mini-openclaw/
├── backend/                    # FastAPI 后端 (Port 8002)
│   ├── app.py                  # 入口 + lifespan 初始化
│   ├── config.py               # 全局配置 (config.json 持久化)
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── api/                    # 6+ 个 API 路由模块
│   │   ├── chat.py             # POST /api/chat (SSE 流式)
│   │   ├── sessions.py         # 会话 CRUD + 标题生成
│   │   ├── files.py            # 文件读写 + 技能列表
│   │   ├── tokens.py           # Token 统计
│   │   ├── compress.py         # 对话压缩
│   │   └── config_api.py       # RAG 模式 + 引擎切换 + 记忆后端切换
│   │
│   ├── graph/                  # Agent 核心逻辑
│   │   ├── agent.py            # AgentManager (统一入口, 引擎切换)
│   │   ├── engines/            # 三套 Agent 引擎
│   │   │   ├── base.py         # BaseEngine 抽象接口
│   │   │   ├── create_agent_engine.py   # 方式1: create_agent 封装
│   │   │   ├── langgraph_engine.py      # 方式2: LangGraph 状态机
│   │   │   └── raw_loop_engine.py       # 方式3: 自研 while 循环
│   │   ├── nodes/              # LangGraph 自定义节点
│   │   │   ├── reason.py       # LLM 思考节点
│   │   │   ├── act.py          # 工具执行节点
│   │   │   ├── retrieve.py     # RAG 检索节点
│   │   │   ├── reflect.py      # 反思节点
│   │   │   └── memory_flush.py # 记忆刷盘节点
│   │   ├── session_manager.py  # 会话持久化 (JSON)
│   │   ├── prompt_builder.py   # System Prompt 6 部分组装
│   │   └── memory_indexer.py   # 混合检索 (EnsembleRetriever)
│   │
│   ├── memory/                 # Dual-Layer 记忆系统
│   │   ├── base.py             # MemoryBackend 抽象接口
│   │   ├── native/             # 自建记忆后端
│   │   │   ├── daily_log.py    # Layer 1: Daily Logs (YYYY-MM-DD.md)
│   │   │   ├── knowledge.py    # Layer 2: MEMORY.md 长期知识库
│   │   │   └── flush.py        # 刷盘: Daily → MEMORY.md 提炼
│   │   ├── mem0_backend.py     # Mem0 备用记忆后端
│   │   └── MEMORY.md           # 长期记忆文件
│   │
│   ├── tools/                  # 5 大核心工具
│   │   ├── __init__.py         # 工具注册工厂
│   │   ├── terminal_tool.py    # 沙箱终端
│   │   ├── python_repl_tool.py # Python 解释器
│   │   ├── fetch_url_tool.py   # 网页抓取 (HTML→Markdown)
│   │   ├── read_file_tool.py   # 沙箱文件读取
│   │   ├── search_knowledge_tool.py  # 知识库搜索
│   │   └── skills_scanner.py   # 技能目录扫描器
│   │
│   ├── providers/              # 多模型 Provider 注册表
│   │   ├── registry.py         # ProviderSpec 注册表
│   │   ├── base.py             # 抽象 Provider 接口
│   │   └── embedding.py        # Embedding 抽象层
│   │
│   ├── workspace/              # System Prompt 组件
│   │   ├── SOUL.md
│   │   ├── IDENTITY.md
│   │   ├── USER.md
│   │   └── AGENTS.md
│   │
│   ├── skills/                 # Agent Skills 目录
│   │   └── get_weather/SKILL.md
│   ├── knowledge/              # RAG 知识库文档
│   ├── sessions/               # 会话 JSON + archive/
│   ├── storage/                # 向量索引持久化
│   └── SKILLS_SNAPSHOT.md      # 启动时自动生成
│
├── frontend/                   # Next.js 14 前端
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # 根布局
│   │   │   ├── page.tsx        # 主页面 (三栏布局)
│   │   │   └── globals.css     # 全局样式
│   │   ├── lib/
│   │   │   ├── store.tsx       # React Context 状态管理
│   │   │   └── api.ts          # SSE 客户端
│   │   └── components/
│   │       ├── chat/
│   │       │   ├── ChatPanel.tsx
│   │       │   ├── ChatMessage.tsx
│   │       │   ├── ChatInput.tsx
│   │       │   ├── ThoughtChain.tsx
│   │       │   └── RetrievalCard.tsx
│   │       ├── layout/
│   │       │   ├── Navbar.tsx
│   │       │   ├── Sidebar.tsx
│   │       │   └── ResizeHandle.tsx
│   │       └── editor/
│   │           └── InspectorPanel.tsx
│   └── package.json
│
├── docs/
├── docker-compose.yml
├── Dockerfile
├── .claudeignore
└── CLAUDE.md
```

### 核心设计决策

| 决策 | 理由 |
|------|------|
| 三套引擎并存 | 教学对比：封装层 vs 状态机 vs 裸循环 |
| 引擎/记忆后端可切换 | config.json 一键切换，前端设置面板可操作 |
| 文件驱动记忆 (Native) | 透明可控，可 git 版本控制，教学核心 |
| Mem0 备用 | 对比工业级 MaaS 方案，拓宽学生视野 |
| Milvus Lite 默认 | 嵌入式零配置，API 与生产级 Milvus 一致 |
| 统一 LangChain 生态 | 一个框架覆盖 Agent + RAG + Tools，降低学习成本 |

---

## 3. 三套 Agent 引擎

### 3.1 引擎切换机制

```python
# config.json
{ "agent_engine": "langgraph" }  // "create_agent" | "langgraph" | "raw_loop"

# graph/agent.py
class AgentManager:
    def _get_engine(self) -> BaseEngine:
        match self.config.agent_engine:
            case "create_agent": return CreateAgentEngine(self.llm, self.tools)
            case "langgraph":    return LangGraphEngine(self.llm, self.tools)
            case "raw_loop":     return RawLoopEngine(self.llm, self.tools)
```

所有引擎实现统一的 `BaseEngine` 接口，产出相同格式的 SSE 事件。

### 3.2 引擎 1: create_agent (生产模式)

使用 LangChain 1.x `create_agent` API，一行构建 Agent。适合快速部署。

### 3.3 引擎 2: LangGraph 状态机 (教学核心)

状态机流程图：

```
START → retrieve (RAG) → reason (LLM) → should_act?
  ├─ yes → act (工具执行) → reason
  └─ no  → reflect (反思) → memory_flush (刷盘) → END
```

自定义节点：

| 节点 | 文件 | 职责 |
|------|------|------|
| retrieve | nodes/retrieve.py | EnsembleRetriever 混合检索 (70% vector + 30% BM25) |
| reason | nodes/reason.py | 调用 LLM，生成文本或 tool_calls |
| act | nodes/act.py | 执行工具调用，收集结果 |
| reflect | nodes/reflect.py | LLM 审视本轮对话，提取值得记忆的信息 |
| memory_flush | nodes/memory_flush.py | 将反思结果写入 Daily Log / 提炼到 MEMORY.md |

### 3.4 引擎 3: 自研 Raw Loop (教学对比)

约 100 行核心代码的 while 循环，直接调用 OpenAI-compatible API。不依赖 LangChain，展示 Agent 的本质。

---

## 4. Dual-Layer 记忆系统

### 4.1 架构

```
config.json: memory_backend: "native" | "mem0"

NativeMemory (自建双层)          Mem0Backend (MaaS 备用)
├─ Layer 1: Daily Logs           └─ mem0.Memory
│  memory/logs/YYYY-MM-DD.md
└─ Layer 2: MEMORY.md
   memory/MEMORY.md
```

### 4.2 Native Memory

**Layer 1 - Daily Logs**: Append-only 追加写入，记录工具调用结果、用户偏好、任务摘要。由 LangGraph reflect 节点触发。

**Layer 2 - MEMORY.md**: 经筛选的高价值长期记忆。结构化分区：用户画像、项目事实、习得技能、关键决策。

**刷盘流程**:
```
Daily Logs (近7天) → LLM 提炼 → 与 MEMORY.md 去重/合并 → 写回 → 重建向量索引
```

### 4.3 混合检索

```python
vector_retriever = MilvusRetriever(embeddings=bge_m3, collection="memory")
bm25_retriever = BM25Retriever.from_documents(memory_docs)
hybrid = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.7, 0.3]
)
```

### 4.4 Mem0 备用方案

通过 `mem0` 库接入，统一 MemoryBackend 抽象接口。config.json 中 `memory_backend: "mem0"` 切换。教学对比点：Native 透明可编辑 vs Mem0 自动结构化提取。

### 4.5 统一接口

```python
class MemoryBackend(ABC):
    async def add_memory(self, content: str, metadata: dict) -> None
    async def search_memory(self, query: str, top_k: int = 5) -> list[MemoryItem]
    async def get_all(self) -> str
    async def flush(self) -> None
```

---

## 5. 多模型 Provider 系统

### 5.1 Provider 注册表

```python
@dataclass
class ProviderSpec:
    name: str               # 配置字段名
    llm_class: str          # LangChain LLM 类路径
    env_key: str | None     # API Key 环境变量名
    display_name: str
    default_model: str
    supports_embedding: bool
    embedding_class: str | None
```

### 5.2 支持的 Provider

| Provider | 默认模型 | Embedding | 接入方式 |
|----------|---------|-----------|---------|
| 智谱 GLM | glm-4-flash | - | langchain-zhipu |
| DeepSeek | deepseek-chat | - | langchain-deepseek |
| OpenRouter | claude-sonnet-4 | - | langchain-openai |
| OpenAI | gpt-4o | text-embedding-3-small | langchain-openai |
| Ollama | qwen2.5:7b | nomic-embed-text | langchain-ollama |
| SiliconFlow | - | BAAI/bge-m3 | OpenAI-compatible |

### 5.3 默认配置

- LLM: GLM-4-Flash (智谱)
- Embedding: BAAI/bge-m3 (SiliconFlow)
- 通过 config.json 切换任意 Provider

---

## 6. 前端设计

### 6.1 三栏 IDE 布局

- 左侧 Sidebar：会话列表 + 设置面板 (引擎切换/记忆后端/RAG 开关) + Token 概览
- 中间 ChatPanel：消息气泡 + 思维链 (可折叠) + RAG 检索卡片 + 对话压缩
- 右侧 InspectorPanel：文件树 + Monaco Editor + Token 统计

### 6.2 四项可视化特性

1. **思维链可视化**: 可折叠面板展示 tool_start → tool_end 全过程，颜色编码
2. **实时文件编辑器**: Monaco Editor 加载 workspace/memory/skills 文件，保存触发索引重建
3. **Token 统计仪表盘**: System Prompt 各部分 + 会话历史的 Token 占用
4. **对话压缩演示**: 展示压缩前后对比，查看归档内容

### 6.3 UI 风格

- 浅色 Apple 风格 (Frosty Glass)，背景 #fafafa，毛玻璃效果
- 强调色：克莱因蓝
- 导航栏左侧："mini OpenClaw"，右侧：GitHub 仓库链接 (https://github.com/hfhfn)

---

## 7. API 接口

### 7.1 PRD 原有接口

| 路径 | 方法 | 说明 |
|------|------|------|
| /api/chat | POST | SSE 流式对话 |
| /api/sessions | GET/POST | 列出/创建会话 |
| /api/sessions/{id} | PUT/DELETE | 重命名/删除会话 |
| /api/sessions/{id}/messages | GET | 完整消息 |
| /api/sessions/{id}/history | GET | 对话历史 |
| /api/sessions/{id}/generate-title | POST | AI 生成标题 |
| /api/sessions/{id}/compress | POST | 压缩对话历史 |
| /api/files | GET/POST | 文件读写 |
| /api/skills | GET | 列出技能 |
| /api/tokens/session/{id} | GET | 会话 Token 统计 |
| /api/tokens/files | POST | 文件 Token 统计 |
| /api/config/rag-mode | GET/PUT | RAG 模式开关 |

### 7.2 新增接口

| 路径 | 方法 | 说明 |
|------|------|------|
| /api/config/engine | GET/PUT | 获取/切换 Agent 引擎 |
| /api/config/memory-backend | GET/PUT | 获取/切换记忆后端 |
| /api/memory/flush | POST | 手动触发记忆刷盘 |
| /api/memory/daily-logs | GET | 获取 Daily Logs 列表 |

### 7.3 SSE 事件类型

| 事件 | 数据 | 触发时机 |
|------|------|---------|
| retrieval | {query, results} | RAG 检索完成 |
| token | {content} | LLM 输出 token |
| tool_start | {tool, input} | 调用工具前 |
| tool_end | {tool, output} | 工具返回后 |
| new_response | {} | 新一轮文本生成 |
| done | {content, session_id} | 响应结束 |
| title | {session_id, title} | 首次对话后生成标题 |
| error | {error} | 异常 |

---

## 8. 部署方案

### 8.1 本地开发

```bash
# 后端
cd backend && pip install -r requirements.txt
uvicorn app:app --port 8002 --host 0.0.0.0 --reload

# 前端
cd frontend && npm install && npm run dev
```

### 8.2 Docker Compose

```yaml
services:
  backend:
    build: ./backend
    ports: ["8002:8002"]
    volumes: ["./backend:/app"]
    env_file: ./backend/.env

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  postgres:  # 可选 pgvector
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    profiles: ["pgvector"]
```

### 8.3 向量数据库

- 默认: Milvus Lite (嵌入式, 单文件 `.db`)
- 可选: pgvector (需 `--profile pgvector`)
- 配置: `config.json` 中 `vector_store: "milvus" | "pgvector" | "faiss"`

---

## 9. "Request too large" 解决方案

创建 `.claudeignore` 排除大文件：

```
docs/工业级智能体记忆系统开发实践.pdf
nanobot/case/
nanobot/.git/
*.gif
*.mp4
```
