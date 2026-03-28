# Research Copilot — 模块化说明

本文档描述当前代码库按职责划分的独立模块、主要文件、输入输出与依赖关系，便于维护与后续拆分服务。

---

## 1. 启动与配置模块（Bootstrap & Config）

| 项目 | 说明 |
|------|------|
| **文件** | `run.py`, `config.py` |
| **职责** | 一键启动后端 FastAPI 与前端 Streamlit；统一管理数据目录、模型名、分块参数、服务地址等 |
| **输入** | 环境变量（如 `DASHSCOPE_API_KEY`、`CHUNK_SIZE`、`BACKEND_HOST` 等） |
| **输出** | 进程编排；全局配置常量 |
| **外部依赖** | 操作系统环境变量、本地文件系统 |

---

## 2. 前端交互模块（UI）

| 项目 | 说明 |
|------|------|
| **文件** | `frontend/app.py` |
| **职责** | PDF 上传、已入库文献列表、跨论文智能问答与引用来源展示 |
| **调用的后端接口** | `GET /health`、`POST /api/papers/upload`、`GET /api/papers/`、`POST /api/chat` |
| **输入** | 用户上传的 PDF、聊天问题 |
| **输出** | Streamlit 页面渲染 |
| **外部依赖** | `streamlit`、`requests`；需后端服务可用 |

---

## 3. API 网关模块（Backend Entry & Routing）

| 项目 | 说明 |
|------|------|
| **文件** | `backend/main.py`、`backend/api/papers.py`、`backend/api/chat.py` |
| **职责** | HTTP 路由、CORS、应用启动时初始化数据库；将请求转发到业务逻辑 |
| **子路由** | `papers`：文献上传 / 列表 / 详情 / 删除；`chat`：问答 |
| **输入** | HTTP 请求（JSON / multipart） |
| **输出** | JSON 响应 |
| **外部依赖** | `fastapi`、`uvicorn` |

---

## 4. 文档解析模块（Parsing）

| 项目 | 说明 |
|------|------|
| **文件** | `backend/core/parser.py` |
| **职责** | 使用 PyMuPDF 读取 PDF，按页抽取文本；启发式提取标题、作者、摘要 |
| **输入** | PDF 文件路径 |
| **输出** | `ParsedPaper`（标题、作者、摘要、全文、分页文本、页数） |
| **外部依赖** | `PyMuPDF`（`fitz`） |

---

## 5. 文本切分模块（Chunking）

| 项目 | 说明 |
|------|------|
| **文件** | `backend/core/chunker.py` |
| **职责** | 按字符窗口对每页文本切分（可配置 overlap），并附带 `paper_id`、页码、块序号 |
| **输入** | 分页文本列表、`paper_id` |
| **输出** | `Chunk` 列表 |
| **配置** | `CHUNK_SIZE`、`CHUNK_OVERLAP`（见 `config.py`） |

---

## 6. 向量化与向量检索模块（Embedding & Vector Store）

| 项目 | 说明 |
|------|------|
| **文件** | `backend/core/embedder.py`、`backend/storage/vectorstore.py` |
| **职责** | 调用 DashScope 文本嵌入 API；将向量与文档写入 Chroma，并按向量相似度检索 |
| **输入** | 文本列表或单条查询文本；检索时还需 `top_k` |
| **输出** | 向量；检索结果（文档片段、元数据、距离等） |
| **外部依赖** | `dashscope`、`chromadb`；本地持久化目录 `CHROMA_DIR` |

---

## 7. RAG 推理模块（Retrieval-Augmented Generation）

| 项目 | 说明 |
|------|------|
| **文件** | `backend/core/rag.py`、`backend/core/llm.py` |
| **职责** | 问题嵌入 → 向量检索 top_k → 组装上下文与系统提示 → 调用大模型生成回答，并整理引用列表 |
| **输入** | 用户自然语言问题 |
| **输出** | 回答文本 + `references`（论文标题、页码、片段等） |
| **外部依赖** | `embedder`、`vectorstore`、`database`（按 `paper_id` 取标题）、`llm`（DashScope Generation） |
| **配置** | `RAG_TOP_K` |

---

## 8. 元数据持久化模块（Metadata Storage）

| 项目 | 说明 |
|------|------|
| **文件** | `backend/storage/database.py` |
| **职责** | SQLite 存储论文元数据（标题、作者、摘要、文件路径、页数、上传时间等） |
| **主要操作** | 初始化表、`insert_paper`、`get_paper`、`list_papers`、`delete_paper` |
| **输入** | 结构化论文字段 |
| **输出** | 查询结果字典或列表 |
| **外部依赖** | 标准库 `sqlite3`；路径 `SQLITE_PATH` |

---

## 端到端数据流

### 文献入库

1. 前端上传 PDF → `POST /api/papers/upload`
2. 保存文件至 `UPLOAD_DIR`
3. `parse_pdf` → `insert_paper`（SQLite）
4. `chunk_pages` → `embed_texts` → `add_chunks`（Chroma）

### 智能问答

1. 前端发送问题 → `POST /api/chat`
2. `rag.ask`：`embed_query` → `query_chunks` → 按需 `get_paper` 补全标题
3. `chat_completion` 生成答案 → 返回 `answer` 与 `references`

---

## 可选：进一步服务化拆分（演进方向）

当前为单仓库、多进程（API + UI），逻辑上已分层。若需独立部署，可演进为：

| 服务 | 大致职责 |
|------|----------|
| UI 服务 | Streamlit 或未来 Web 前端 |
| API 服务 | FastAPI 路由与编排 |
| 知识服务 | 解析、切分、向量化、索引写入（可接异步队列） |
| 问答服务 | 检索 + LLM 生成（可单独扩缩容） |

---

## 相关文件索引

| 模块 | 路径 |
|------|------|
| 配置 | `config.py` |
| 启动脚本 | `run.py` |
| 依赖清单 | `requirements.txt` |
| 产品需求（愿景与规划） | `需求文档.md` |

文档版本与代码库同步维护；若接口或目录变更，请一并更新本文件。
