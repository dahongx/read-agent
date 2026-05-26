# 实现说明

文献阅读 Agent 的完整技术实现文档。覆盖前后端架构、数据流、关键模块设计、API 契约。

---

## 一、系统总览

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     浏览器 (React 19 + Vite + Tailwind)                  │
│                                                                          │
│  UploadPage  →  ProgressPage  →  PptViewerPage                          │
│       │              │                  │                                │
│       │              │      ┌───────────┴──────────────┐                │
│       │              │      │ 左：SVG 幻灯片 + speaker notes + TTS    │  │
│       │              │      │ 右：ChatPanel（多会话）                │  │
│       │              │      │       │                                │  │
│       │              │      │       └─ PdfViewer（PDF.js phrase 高亮） │
│       │              │      └────────────────────────────┘             │
└───────┼──────────────┼─────────────────────────────────────────────────┘
        │              │  HTTP REST + WebSocket
┌───────▼──────────────▼─────────────────────────────────────────────────┐
│                    FastAPI (uvicorn, Python 3.11)                      │
│                                                                         │
│  api/upload     api/spaces      api/chat       api/sessions             │
│   │ user_id      │ list/get     │ /api/chat    │ session 兼容            │
│   │ + space_id   │ /pdf /slides │ planner+RAG  │                        │
│   ↓              │ /script /ppt │ +LLM 答题    │                        │
│  task_manager   │ /conversations│              │                        │
│   ├ ppt_task    │              │              │                        │
│   │  └ ppt_generator → subprocess(claude CLI) → /ppt-master skill      │
│   │                                                                     │
│   └ rag_task                                                            │
│      └ rag_index.build_index                                            │
│           ├─ pypdf 抽文本 + 启发式去 header                              │
│           ├─ 段落切 chunk（带 page metadata）                            │
│           ├─ BGE-m3 编码 → LlamaIndex VectorStoreIndex                  │
│           └─ rank_bm25 语料落盘 bm25_corpus.json                         │
│                                                                         │
│  问答时：                                                                │
│   chat → plan_query (Haiku，多文档 space 才调) →                          │
│          retrieve_from_index (hybrid + 可选 rerank + plan 路由) →        │
│          OpenAI SDK → zhengmi 网关 → Claude Sonnet 4.6                  │
│                                                                         │
│  持久化：spaces/<sid>.json   conversations/<uid>/<sid>/*.json           │
│         cache/ppt/<sid>/   cache/rag/<hash>-v7/                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 关键技术栈

| 层 | 选型 |
|---|---|
| 后端 | FastAPI + uvicorn + asyncio |
| 任务调度 | `asyncio.create_task` + `asyncio.gather`（PPT/RAG 并行） |
| PPT 生成 | subprocess 调 Claude CLI → ppt-master skill（不在主进程内） |
| 嵌入模型 | BGE-m3（本地 HuggingFace 加载，CPU 推理） |
| 向量检索 | LlamaIndex VectorStoreIndex (in-memory) |
| 关键词检索 | rank-bm25（语料 JSON 落盘，内存缓存按 mtime） |
| Rerank（可选） | bge-reranker-base（CPU 友好；v2-m3 需 GPU） |
| 答题 LLM | Claude Sonnet 4.6（zhengmi 网关，OpenAI 兼容） |
| 规划 LLM | Claude Haiku 4.5（zhengmi，更快更便宜，只跑 multi space） |
| 前端 | React 19 + Vite + react-router-dom v7 + Tailwind 4 |
| PDF 查看 | 自定义 PDF.js viewer（含 PDFFindController 短语高亮） |
| 实时推送 | WebSocket（`/ws/<session_id>`），HTTP 轮询兜底（8s） |
| 持久化 | 本地文件系统（JSON 元数据 + 缓存目录），无数据库 |

### 1.3 核心概念

| 概念 | 标识 | 生命周期 | 关键作用 |
|---|---|---|---|
| **task**（生成任务） | `task_id` (UUID) | 短期，跑完即结束 | 一次"上传 + 跑 PPT/RAG"的执行体；内存里有 `SessionState` |
| **space**（知识空间） | `space_id = <pdf_hash>-<config_hash>` | 永久 | 一份生成产物，跨用户共享；元数据落盘 `spaces/<sid>.json` |
| **conversation**（对话） | `conv_id` (UUID hex) | 永久 | 按 `(user_id, space_id)` 隔离，存盘 |
| **user** | localStorage 字符串 | 浏览器持有 | 无注册无密码，输入即用 |

---

## 二、目录结构

### 2.1 后端 `backend/`

```
backend/
├── main.py                   # FastAPI app 入口、路由注册、SPA 静态托管
├── chat_cli.py               # 终端调试工具：复用 chat 链路做 CLI 问答
├── inspect_rag.py            # 旧工具，dump 一个 RAG 索引内容
├── start.bat / start_prod.bat
├── requirements.txt
├── .env / .env.example
├── app/
│   ├── core/
│   │   ├── config.py         # Settings (pydantic-settings)，含 LLM/RAG/Reranker 全部参数
│   │   └── startup.py        # lifespan: 启动时预热 BGE-m3
│   ├── models.py             # 所有 pydantic schema（PptConfig / SessionState / etc.）
│   ├── api/
│   │   ├── upload.py         # /api/upload, /api/upload-multi  (建 session + space)
│   │   ├── spaces.py         # /api/users/{uid}/spaces, /api/spaces/{sid}/*  (空间 / 对话)
│   │   ├── sessions.py       # /api/sessions/{id}  (旧 session 兼容查询)
│   │   ├── chat.py           # /api/chat  (规划 + 检索 + 答题 + 引用解析)
│   │   ├── script.py         # /api/sessions/{id}/script  (兼容旧前端)
│   │   └── ws.py             # /ws/{id}  (进度与日志实时推送)
│   └── services/
│       ├── task_manager.py   # 任务协调，并发 PPT + RAG；状态机；广播
│       ├── ppt_generator.py  # 调 Claude CLI，监听 stdout/stderr，产物兜底恢复
│       ├── rag_index.py      # 索引构建：chunk + BGE 嵌入 + BM25 语料；query_index 做 hybrid+RRF
│       ├── rag.py            # retrieve / retrieve_from_index，含 plan 路由
│       ├── reranker.py       # CrossEncoder lazy load
│       ├── query_planner.py  # Haiku 决定 scope / doc_id / subqueries
│       ├── space_store.py    # spaces/<sid>.json CRUD + 状态字段
│       ├── conversation_store.py  # conversations/<uid>/<sid>/ CRUD
│       ├── session_store.py  # in-process dict，存运行时 SessionState
│       ├── session_paths.py  # 路径工具
│       ├── session_logs.py   # 日志写盘 + 内存 ring buffer
│       ├── connection_manager.py  # WebSocket 连接池
│       └── dev_mode.py       # 开发模式 fixture
├── models/bge-m3/            # 本地 BGE-m3 嵌入模型（首次自动下载）
└── uploads/                  # 数据存放（运行时生成，已 gitignore）
    ├── spaces/<sid>.json
    ├── conversations/<uid>/<sid>/{index.json, <conv_id>.json}
    ├── sessions/<task_id>/{input,output,logs}/
    └── cache/
        ├── ppt/<sid>/{multi_survey_xx_ppt169_*/, project_manifest.json}
        └── rag/<hash>-v7/{docstore.json, default__vector_store.json, bm25_corpus.json}
```

### 2.2 前端 `frontend/src/`

```
src/
├── main.tsx                  # React Router 入口
├── index.css                 # Tailwind 全局
├── pages/
│   ├── UploadPage.tsx        # 用户名 + 上传 + 我的历史
│   ├── ProgressPage.tsx      # WebSocket 进度 + 日志
│   └── PptViewerPage.tsx     # 阅读页（左 PPT + 右 ChatPanel）
├── components/
│   ├── ChatPanel.tsx         # 问答 + 会话切换 + 语音 + TTS
│   ├── PdfViewer.tsx         # 模态 PDF 查看器，拼 viewer.html URL
│   └── Layout.tsx            # 顶栏框架
├── hooks/
│   └── useWebSocket.ts       # 重连、消息流、状态机
├── utils/
│   ├── user.ts               # localStorage user_id + useUserId hook
│   ├── api.ts                # spaces / conversations 的 fetch 封装
│   └── tts.ts                # TTS 文本预处理
└── public/pdfjs/             # 自定义 PDF.js viewer
    ├── viewer.html           # 加了 PDFFindController + search hash 解析
    ├── pdf.min.mjs
    ├── pdf_viewer.mjs
    └── ...
```

---

## 三、数据持久化设计

无数据库，全部文件 JSON。

### 3.1 Space 元数据 `spaces/<sid>.json`

```json
{
  "space_id": "5fafbc5d7f062de6-b5a08452-86e9e44e",
  "pdf_filename": "2603.16862v1.pdf, preprints202602.1990.v1.pdf",
  "pdf_path": "",
  "pdf_hash": "multi",
  "config": {
    "template": "academic_defense", "page_count": 12,
    "language": "中文", "style": "学术汇报", "audience": "高校师生"
  },
  "paper_title": "多篇综述 (2)",
  "session_type": "multi",
  "source_documents": [
    {"doc_id": "doc_001", "order": 1, "source_file_name": "2603.16862v1.pdf",
     "pdf_path": "...", "content_hash": "..."},
    {"doc_id": "doc_002", ...}
  ],
  "contributors": ["alice", "bob"],
  "state": "ready",
  "error_message": null,
  "created_at": 1716700000.0,
  "updated_at": 1716700300.0,
  "last_accessed_by": {"alice": 1716700300.0, "bob": 1716700200.0}
}
```

- `space_id` 等于 `compute_cache_key(pdf, config)` 或 `compute_multi_cache_key(pdfs, config)`，PPT/RAG 缓存路径也按此键
- `contributors` 记录所有访问过该空间的 user_id，列表"我的历史"靠这个反查
- `state ∈ {pending, ready, failed}` 由 task_manager 在任务结束时写

### 3.2 Conversation `conversations/<uid>/<sid>/`

```
conversations/alice/5fafbc5d.../
├── index.json                # [{id, title, msg_count, created_at, updated_at}, ...]
└── <conv_id>.json            # {id, title, messages: [...], created_at, updated_at}
```

`<conv_id>.json` 里的每条 message：

```json
{
  "role": "assistant",
  "content": "M+ 通过长期记忆池扩展...（第3页）。在 LongBench 上...(第6页)",
  "sources": [
    {"chunk_id": 1, "page": 3, "doc_id": "doc_001", "file": "M+: ...",
     "source_file_name": "2502.00592v2.pdf", "quote": "we extend MemoryLLM...",
     "text": "...preview...", "full_text": "...完整 chunk..."}
  ],
  "ts": 1716700000.0
}
```

每空间最多 50 条会话（上限可在 `conversation_store.py` 改）。

### 3.3 PPT 缓存 `cache/ppt/<space_id>/`

```
cache/ppt/<space_id>/
├── project_manifest.json     # {project_dir, ppt_path, slides_dir, notes_dir, cache_key, updated_at}
└── multi_survey_xxx_ppt169_20260526/   ← Claude CLI + ppt-master 生成
    ├── design_spec.md
    ├── sources/              # 各 PDF + 转出的 markdown + 抽出的图片
    ├── templates/            # 选中的版式 SVG
    ├── svg_output/           # Executor 阶段
    ├── svg_final/            # finalize_svg.py 处理后
    ├── notes/total.md + 01_*.md ...
    └── multi_survey_xxx_*.pptx (+ _svg.pptx)
```

### 3.4 RAG 缓存 `cache/rag/<key>/`

```
cache/rag/<pdf_hash>-v7/                 ← 单文档（v7 = cache_version）
├── docstore.json                        ← LlamaIndex 节点库（含 metadata.page_label）
├── default__vector_store.json           ← BGE-m3 向量
├── index_store.json
├── graph_store.json
├── image__vector_store.json
└── bm25_corpus.json                     ← [{node_id, text, metadata}, ...]

cache/rag/<key>-multi-v2/                ← 多文档同结构，metadata 多 doc_id/doc_order
```

cache_version：单文档 `v7`，多文档 `multi-v2`。每次结构性升级 bump 一次，旧索引自动失效重建。

---

## 四、后端关键模块详解

### 4.1 `services/space_store.py`

只做 JSON CRUD + 简单查询：

| 函数 | 行为 |
|---|---|
| `upsert(space_id, user_id, config, ...)` | 新建/更新空间；若旧 state=failed，重置为 pending（视为重试） |
| `get(space_id)` | 读 `spaces/<sid>.json` |
| `touch_access(space_id, user_id)` | 更新 `last_accessed_by[user]` + 加入 contributors |
| `list_for_user(user_id)` | 扫所有 spaces/\*.json，按 `last_accessed_by[user]` 倒排 |
| `mark_state(space_id, state, error_message=None)` | task_manager 在 ready/failed 时调 |
| `delete_space(space_id)` | 只删 spaces/<sid>.json；缓存不动 |

### 4.2 `services/conversation_store.py`

| 函数 | 关键 |
|---|---|
| `create_conversation(uid, sid, title=None)` | 50 条上限超时抛 ValueError；写 `<conv_id>.json` + index.json |
| `append_message(uid, sid, conv_id, role, content, sources)` | 追加 + 更新 index.json 的 msg_count |
| `get_conversation(uid, sid, conv_id)` | 读完整消息流 |
| `list_conversations(uid, sid)` | 读 index.json |
| `rename(...)` | 改 title 到 60 字以内 |
| `delete_conversation(...)` | 删 `<conv_id>.json` + 移出 index.json |

`_safe_id()` 会把 user_id / space_id 里非 `[A-Za-z0-9_\-.]` 字符替换为 `_`，防止路径穿越。

### 4.3 `services/rag_index.py`

#### 索引构建 `build_index(pdf_path, index_dir)`

```python
1. pypdf.PdfReader 解析
2. _extract_title()    启发式取标题（PDF metadata > 首页第一行）
3. 检测 ≥3 页都出现的前 3 行 → 页眉过滤
4. for page in pages:
     _split_into_paragraphs(text)
     _group_paragraphs(累到 ~1200 字 flush)
   每个 chunk 必带 metadata:
     {page_label, page_number, file_name, paper_title,
      [+ doc_id, doc_order, source_file_name, content_hash 多文档时]}
5. BGE-m3 编码所有 chunk → VectorStoreIndex(persist_dir=index_dir)
6. _persist_bm25_corpus()  写 bm25_corpus.json：
     [{node_id, text, metadata}, ...]
```

#### 检索 `query_index(index_dir, question)` —— Hybrid Search + RRF

```python
1. Dense: VectorIndexRetriever, similarity_top_k=15
2. BM25: 加载 bm25_corpus.json 用 _tokenize（中文按字、英文按词）
        BM25Okapi.get_scores → top 15
   首次构建后 BM25Okapi 按 mtime 缓存到内存，复用免重建
3. RRF 融合 (k=60):
     score(d) = Σ 1 / (60 + rank_in_each_list)
4. 返回前 max(15) 个 chunk dict（含 full_text/page/doc_id 等）
```

BM25 corpus 缺失时自动降级为 dense-only。

#### `_tokenize(text)` 中英分词

```python
中文字符 → 单字
连续 alphanum → word
其它 → 分隔符
```

简单但对论文检索足够；不引入 jieba 等重依赖。

### 4.4 `services/reranker.py`

懒加载 sentence-transformers CrossEncoder：

```python
rerank(question, candidates, top_k=6) → top_k 个 chunk（带 rerank_score）
```

- `RERANKER_ENABLED=false` 时直接 `candidates[:top_k]` 返回（按 RRF 顺序截断）
- 模型加载或 predict 异常 → 同上降级
- 默认模型 `bge-reranker-base` (~278M params)；要更高质量改 `bge-reranker-v2-m3`（要 GPU）

### 4.5 `services/query_planner.py` —— 多文档查询路由

#### 输入

```
question: "两篇论文分别有什么创新的点"
source_documents: [
  {doc_id: "doc_001", source_file_name: "2603.16862v1.pdf"},
  {doc_id: "doc_002", source_file_name: "preprints202602.1990.v1.pdf"}
]
```

#### 调用 Claude Haiku 4.5

System prompt 教模型只输出 JSON：

```json
{
  "scope": "all" | "single",
  "doc_id": "doc_xxx" | null,
  "subqueries": ["...", "..."]
}
```

判断规则（写在 system prompt 里）：
- "两篇/分别/对比/它们/各自" → scope=all，每篇一个不同 subquery
- 明确指出某篇（标题、Chronos/M+） → scope=single + doc_id + 一个 subquery
- 含糊问题 → scope=all + **一个** subquery（不重复）

#### 输出 `QueryPlan` dataclass

```python
@dataclass
class QueryPlan:
    scope: str = "all"                    # all | single
    doc_id: str | None = None
    subqueries: list[str] = []
    raw: str | None = None                # 调试用
```

#### 容错

- JSON 解析失败 → 第二次尝试用正则抓 `{...}`
- 模型 hallucinate 不存在的 doc_id → 降级 scope=all
- 整个 LLM 调用挂了 → fallback `scope=all, subqueries=[原问]`
- 同一 (space_id, question) 内存缓存 5 分钟

#### 触发条件

仅 `len(source_documents) > 1` 才调用（单文档无意义）。

### 4.6 `services/rag.py`

把 planner 和 retriever 组合起来：

```python
retrieve_from_index(index_dir, question, plan=None) → (context_text, sources)

  if plan is None or 无 subqueries:
      → 单 query：query_index + rerank top final_k
  elif plan.scope == "single":
      → query_index 后按 doc_id 过滤候选，rerank top final_k
  elif plan.scope == "all" and 多 subquery:
      per_query_k = max(2, final_k // n + 1)
      每个 subquery 独立 retrieve+rerank top per_query_k
      合并去重（key = doc_id + filename + page + text 前 120 字）
      截到 final_k
```

去重 key 保证多 subquery 即便召回相同 chunk 也只算一次。

### 4.7 `services/ppt_generator.py`

#### `compute_cache_key(pdf_path, config) → "<pdf_hash[:16]>-<config_hash[:8]>"`

单文档；这个 key 直接当 `space_id` 用。

#### `compute_multi_cache_key(pdf_paths, config) → "<hash[:16]>-<config_hash[:8]>-<merge_hash[:8]>"`

多文档同理。

#### `run_ppt_generation(session_id, pdf_path, config, output_dir, ...)`

```python
1. 拼 [BATCH_MODE] prompt：八项确认 + 模板/页数/语言/受众
   强制 skill 跳过 BLOCKING 等待，不调用 AskUserQuestion
2. subprocess.Popen([
     claude_exe, "--print", "--verbose",
     "--output-format", "stream-json",
     "--dangerously-skip-permissions",
     "--add-dir", output_dir,
     "--add-dir", pdf_dir,
     "--add-dir", REPO_ROOT,
     "--model", "sonnet",
     prompt
   ], stdout=PIPE, stderr=PIPE, encoding="utf-8", env={...CLAUDE_CODE_GIT_BASH_PATH})
3. 两条线程并发读 stdout/stderr → 通过 asyncio.run_coroutine_threadsafe
   推到 log_recorder + WebSocket
4. 每 2s 扫 output_dir 找产物：
     notes/*.md      → 30%
     svg_output/*.svg → 55%
     svg_final/*.svg  → 75%
     *.pptx           → 95%
5. 60s 无新输出推 claude_idle WARNING
6. Claude 退出后 _find_latest_project + _project_artifact_state 检测：
     state ∈ {empty, partial, final}
   non-final 时 Python 直接调三个 skill 脚本兜底：
     total_md_split.py + finalize_svg.py + svg_to_pptx.py
7. 仍 non-final 抛 GenerationError
```

#### 多文档增强 `run_multi_ppt_generation`

额外步骤：
- `project_manager.py init` 建项目
- `import-sources` 拷贝各 PDF + 转 markdown
- `prepare_multi_project_sources()` 拼 `merged.md`（含每篇标题 + doc_id + 全文）
- 用 `_build_multi_batch_prompt` 引导 skill 走综述模式
- 任务结束发现 `state != final` 时调 `_resume_incomplete_multi_project` 重启 skill 补齐

#### Windows GBK 兼容

`pdf_to_md.py` 在 sys.platform=='win32' 强制 stdout UTF-8，避免 `©` 等字符触发 GBK 编码崩溃。`prepare_multi_project_sources` 在发现 import-sources 漏 md 时直接调 pdf_to_md.py 兜底。

### 4.8 `services/task_manager.py`

```python
async def run_tasks(session_id, pdf_path, config):
    session_store.update_status(processing)
    ppt = _ppt_task(...)        # 缓存命中 → 跳过；否则 run_ppt_generation
    rag = _rag_task(...)        # 缓存命中 → 跳过；否则 build_index
    await asyncio.gather(ppt, rag)
    session_store.update_status(ready)
    _sync_space_state(session_id, "ready")
    ws.broadcast({"event": "done"})

    except Exception:
        update_status(error); _sync_space_state("failed", str(exc))
        ws.broadcast({"event": "error"})
```

`_ppt_task` 关键点：

```python
try:
    project_dir = await run_ppt_generation(...)
except Exception as exc:
    # 即使 Claude CLI 收尾报错，产物完整就按成功处理
    recovered = _find_latest_project(cache_dir)
    if recovered and _project_artifact_state(recovered)["state"] == "final":
        log WARNING "recover_after_error"
        project_dir = recovered
    else:
        raise

save_cached_project_outputs(cache_dir, outputs, cache_key)
session_store.update_path_fields(ppt_path=..., slides_dir=..., notes_dir=...)
```

这个兜底是为了 Windows 下 Claude CLI 在 templates 拷贝阶段偶尔抛 WinError 3，但产物其实已全生成的场景。

`_broadcast_progress` 把 `(task, step, pct, stage, status)` 推到 WebSocket，同时更新内存里 SessionState 的 stages。

### 4.9 `api/chat.py` —— 问答主入口

```python
POST /api/chat
body: { session_id?, space_id?, conversation_id?, user_id, question }

1. _resolve_retrieval(req):
     有 session_id 且内存里有 → mode="session", target=session_id
     否则有 space_id：
       内存里能找到该 space 的活跃 session → mode="session"
       否则按 space.pdf_hash 推断 RAG cache 目录 → mode="index_dir"
     都没有 → 400 / 404 / 409

2. 5min in-process LRU 命中？直接返回（key = conversation_id + question + model）

3. plan = None
   if space.source_documents 长度 > 1:
       plan = plan_query(question, space_id, source_documents)

4. retrieve_from_index(index_dir, question, plan=plan)  # 见 §4.6
     → context, sources

5. user_content = "以下是检索到的论文相关片段：\n\n{context}\n\n用户问题：{q}..."
   client.chat.completions.create(
     model=claude-sonnet-4-6,
     messages=[{system}, {user}],
     max_tokens=1500, temperature=0.2
   )

6. _strip_citation_block(raw_answer):
     正则切出 <CITATIONS>...</CITATIONS> 里的 JSON
     返回 (cleaned_answer, citations_list)

7. _attach_quote_to_sources(answer, citations, sources):
     按 chunk_id 优先把 quote 绑回 source
     失败用 page 回退；同 page 多次引用允许多份
     去重 key = (doc_id, page, normalized_quote)
     未在 JSON 出现但答案有的 (第N页) 补一个 fallback source

8. conversation_store.append_message(user/assistant)
   if 首条问答: 异步调 LLM 起 12 字标题 → conversation_store.rename

9. space_store.touch_access(space_id, user_id)

10. 缓存 + 返回 {answer, sources, conversation_id, conversation_title}
```

#### `_normalize_quote(text)`：稳定化引用

LLM 给的 quote 偶尔含会让 PDF.js phrase search 失配的字符。处理：

- 折空格 `\s+ → " "`
- 删不可见字符（U+00AD 软连字符 / U+200B 零宽空格 / BOM 等）
- ligature 还原（ﬁ→fi, ﬂ→fl, ﬃ→ffi 等）
- 检测到 em dash `—` / 中文破折号 / 省略号 / `--` 时**截到它前面**（位置 ≥8 才截，太短无意义）
- 截到 200 字以内

策略：宁可短不要错，让前端高亮稳定命中。

### 4.10 `api/spaces.py`

```
GET    /api/users/{uid}/spaces         → 我的历史空间（含 state）
GET    /api/spaces/{sid}?user_id=X     → 空间元数据 + outputs (touch_access)
DELETE /api/spaces/{sid}?user_id=X     → 删 space.json + 该用户的会话目录

GET    /api/spaces/{sid}/pdf           → 该 space 的 PDF（单文档时）
GET    /api/spaces/{sid}/pdf/{doc_id}  → 多文档时指定文档
GET    /api/spaces/{sid}/slides        → 列出 svg_final/*.svg 文件名
GET    /api/spaces/{sid}/slides/{filename}  → 取单个 SVG
GET    /api/spaces/{sid}/ppt           → 下载 .pptx
GET    /api/spaces/{sid}/script        → 拆分后的 speaker notes 列表

GET    /api/spaces/{sid}/conversations          → 列表
POST   /api/spaces/{sid}/conversations          → 新建
GET    /api/spaces/{sid}/conversations/{cid}    → 详情（含 messages）
PATCH  /api/spaces/{sid}/conversations/{cid}    → 改 title
DELETE /api/spaces/{sid}/conversations/{cid}    → 删除
```

`_resolve_outputs(space_id)` 直接读 `cache/ppt/<sid>/project_manifest.json`，不依赖 session_store；这是 space 跨进程重启仍可用的根基。

### 4.11 `api/upload.py`

```
POST /api/upload (单)
POST /api/upload-multi (多)

form: file(s), ppt_config (JSON), user_id

1. 校验 .pdf 后缀
2. _save_upload_file()  落盘 sessions/<task_id>/input/
3. compute_cache_key() = space_id（与 PPT 缓存键一致）
4. space_store.upsert(space_id, user_id, ..., state=pending)
5. session_store.create_session + set_user_and_space + set_paths + set_ppt_config
6. asyncio.create_task(task_manager.run_tasks(...))
7. 返回 { session_id, status=pending, space_id, cache_hit=false }
```

返回 space_id 前端可立即跳进度页（带 ?space=<sid> query），生成完直接跳 `/space/<sid>`。

---

## 五、前端关键模块

### 5.1 路由 `main.tsx`

```tsx
<Routes>
  <Route element={<Layout />}>
    <Route path="/" element={<UploadPage />} />
    <Route path="/tasks/:id" element={<ProgressPage />} />
    <Route path="/space/:spaceId" element={<PptViewerPage />} />
    {/* 旧 URL 兼容 */}
    <Route path="/session/:id" element={<ProgressPage />} />
    <Route path="/session/:id/ppt" element={<Navigate to="/" replace />} />
  </Route>
</Routes>
```

### 5.2 `utils/user.ts` —— 用户标识

```ts
useUserId(): [string, (v: string) => void]
getUserId(): string
withUserQuery(url): string
```

localStorage key = `read_agent_user_id`。变更时 dispatch `'user-id-changed'` 自定义事件 + `storage` 事件，让多个 hook 同步。

### 5.3 `utils/api.ts` —— REST 客户端

类型化封装：`listSpaces`, `getSpace`, `listConversations`, `getConversation`, `createConversation`, `renameConversation`, `deleteConversation`, `deleteSpace`。所有调用自动 `?user_id=<uid>`。

### 5.4 `pages/UploadPage.tsx`

```
┌─ 顶部：用户名输入栏（onBlur/Enter 提交到 localStorage）─┐
├─ 模式 tabs：单篇 / 多篇综述                            │
├─ 文件拖放区（带选中态视觉反馈）                          │
├─ PptConfig 表单（5 个字段，默认值预填）                  │
├─ 「上传并生成 PPT」按钮                                │
└─ 「我的历史空间」列表（按 state 三种徽章 + 删除按钮）─┘
```

上传成功后 `navigate('/tasks/<task_id>?space=<space_id>')`。

历史空间状态徽章：
- `state === 'ready'` 渲染 `<Link to="/space/...">` 可点击
- `pending / failed` 渲染 disabled `<div>`，失败时显示 error_message tooltip
- 全部都有 ✕ 删除按钮

### 5.5 `pages/ProgressPage.tsx`

```tsx
useWebSocket(taskId) → { lastMessage, readyState }

收到 event:
  - progress: 更新 stages.{ppt|rag}
  - log:     追加到 logs (limit 200)
  - done:    跳转 /space/<space_id>
  - error:   显示 errorDetail
  - status (session snapshot): 全量更新

兜底：每 8s GET /api/sessions/<id> 拉一次（万一 ws 不可用）
```

`spaceId` 优先从 URL query (`?space=...`) 取；后端 snapshot 里也带 `space_id` 字段，确保 done 时能正确跳转。

底部黑底 "实时日志" 滚动框显示所有源（ppt/rag/system）日志，按 level 上色（INFO 灰 / WARN 黄 / ERROR 红）。

### 5.6 `pages/PptViewerPage.tsx`

```tsx
useParams: { spaceId }

useEffect → GET /api/spaces/<spaceId>/slides    设 slides[]
useEffect → GET /api/spaces/<spaceId>/script    设 script[]

布局：grid-cols-[3fr_2fr]
  左：
    <img src=`/api/spaces/${spaceId}/slides/${slides[current]}`>
    讲稿折叠面板
    [← / 页码 / →] [▶ 连续播报] [下载]
  右：
    <ChatPanel spaceId={spaceId} />

TTS 连续播报：autoPlayingRef + scriptRef + currentRef
  speakSlideAt(index)：utterance.onend → 自动 setCurrent(next) → 递归
```

键盘 ← / → 翻页。

### 5.7 `components/ChatPanel.tsx`

```tsx
useEffect(spaceId 变化):
  listConversations() → 有则 setActiveConvId(首个)；无则 createConversation()

useEffect(activeConvId 变化):
  getConversation(spaceId, activeConvId) → setMessages(...)

sendText(text):
  setMessages(prev + user message)
  POST /api/chat { space_id, conversation_id, user_id, question }
  setMessages(prev + assistant message with sources)
  若返回 conversation_title → refreshConversations(刷新列表显示新标题)
```

会话切换下拉：

```tsx
{convMenuOpen && (
  <div class="absolute ...">
    <button onClick={handleNewConversation}>+ 新建</button>
    {conversations.map(c => (
      <button onClick={() => setActiveConvId(c.id)}>
        {c.title} ·{c.msg_count}
        <button onClick={handleDelete}>✕</button>
      </button>
    ))}
  </div>
)}
```

答案渲染 `renderWithCitations(text, sources, onPageClick)`：

```ts
正则切 (第N页) | （第N页） 出文字段 + 按钮交替
按钮点击 → findSourceForPage(sources, N) → setPdfTarget({page, docId, fileLabel, quote})
findSourceForPage 优先返回带 quote 的 source，保证 PDF 高亮可命中
```

### 5.8 `components/PdfViewer.tsx`

```tsx
拼 URL：
  /pdfjs/viewer.html?file=<encoded-pdf-url>#page=N&search=<encoded-quote>&phrase=true&highlightAll=true

iframe key 强制 quote 变化时重新加载
ESC 关闭
```

### 5.9 `public/pdfjs/viewer.html` —— 自定义 PDF.js viewer

仅 200 行的简化版（不是完整 PDF.js viewer，是定制版）：

```js
import { EventBus, PDFViewer, PDFLinkService, PDFHistory, PDFFindController }
  from './pdf_viewer.mjs';

// 同时兼容 query string 和 hash 参数
const params = readParams();
const fileUrl = params.get('file');
const startPage = parseInt(params.get('page') || '1', 10);
const searchQuery = params.get('search') || '';
const phraseSearch = params.get('phrase') !== 'false';

const pdfFindController = new PDFFindController({ linkService, eventBus });
const pdfViewer = new PDFViewer({ ..., findController: pdfFindController });

eventBus.on('pagesinit', () => {
  pdfViewer.currentPageNumber = startPage;
});

// 关键：textLayer 渲染完成后才触发查找，避免高亮压错行
eventBus.on('textlayerrendered', evt => {
  if (evt.pageNumber !== startPage) return;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    eventBus.dispatch('find', {
      source: window, type: '',
      query: searchQuery, phraseSearch, highlightAll: true,
    });
  }));
});
```

`pagesinit` 时 PDF 元信息加载完但目标页 textLayer 还没渲染，过早触发 find 会按错误坐标画高亮（视觉错位）。改成 `textlayerrendered` + 两次 rAF 后才 dispatch，对齐稳定。

---

## 六、完整调用链路

### 6.1 上传 → 生成 → 阅读

```
1. UploadPage 输用户名 + 选 PDF + 选配置 → 点上传
2. POST /api/upload  (form: file, ppt_config, user_id)
     → upload.py
        session_store.create_session()
        compute_cache_key() = space_id
        space_store.upsert(space_id, ...)
        asyncio.create_task(task_manager.run_tasks(...))
        return { session_id, space_id, status: pending }
3. 前端 navigate(`/tasks/${session_id}?space=${space_id}`)
4. ProgressPage 打开 WebSocket /ws/<session_id>
5. task_manager.run_tasks 并行：
    _ppt_task:
      compute_cache_key → space_id
      命中 cache？manifest 完整 → 跳过
      否则 run_ppt_generation:
        subprocess.Popen(claude CLI ... [BATCH_MODE] /ppt-master)
        Claude 内部走 ppt-master 7-Step 管道
        Python 兜底 finalize/export
      save_cached_project_outputs(cache_dir, ..., space_id)
      session_store.update_path_fields(slides_dir=..., ppt_path=...)
    _rag_task:
      pdf_hash → cache_key = <hash>-v7
      命中？跳过
      否则 build_index:
        pypdf 抽 → 段落 chunk → BGE-m3 编码 → persist + bm25_corpus.json
      session_store.update_path_fields(rag_index_path=...)
   asyncio.gather 完成 →
     session_store.update_status(ready)
     _sync_space_state(space_id, "ready")
     ws.broadcast({event: done})

6. ProgressPage 收 done → navigate(`/space/${space_id}`)
7. PptViewerPage：
     GET /api/spaces/<sid>/slides → 加载 svg 列表
     GET /api/spaces/<sid>/script → 加载讲稿
   左侧渲染 PPT，右侧渲染 ChatPanel
```

### 6.2 从历史空间进入

```
1. 首页 GET /api/users/<uid>/spaces → 历史卡片
2. 点 "可阅读" → navigate(`/space/<sid>`)
3. PptViewerPage 同 6.1 第 7 步
   注：此时 session_store 内存里可能没有这个 space 的 session（进程重启），
       但 spaces.py 的 outputs 是直接读 ppt cache manifest，照常拿到产物
4. ChatPanel:
     listConversations() → 自动加载最近会话
     getConversation() → 拉历史消息
```

### 6.3 问答

```
1. 用户提问 → POST /api/chat
     body: { space_id, conversation_id, user_id, question }
2. chat.py _resolve_retrieval:
     无 session → 按 space.pdf_hash 推断 RAG cache 目录
3. cache miss → 继续
4. space.source_documents.length > 1 → plan_query (Haiku 4.5)
     返回 QueryPlan(scope, doc_id, subqueries)
5. retrieve_from_index(index_dir, question, plan):
     scope=single → query_index + doc_id 过滤 + rerank
     scope=all + 多 sub → 各 sub 独立 retrieve+rerank → 合并去重
     单文档 / 含糊 → 单 query 走 hybrid + rerank
6. context = "[片段1 | 来自《title》第3页]\n<full_text>\n\n---\n\n..."
7. OpenAI SDK → zhengmi → Sonnet 4.6
     system: 强制 (第N页) + <CITATIONS> JSON
     user: 论文片段 + 问题
8. _strip_citation_block → cleaned_answer + citations[{page, quote, chunk_id}]
9. _attach_quote_to_sources:
     按 chunk_id 把 quote 绑回 source；quote 走 _normalize_quote 清洗
10. conversation_store.append_message(user/assistant)
    if 首问 → 异步起标题 + rename
11. 返回 { answer, sources: [{page, quote, chunk_id, ...}], conversation_id, conversation_title }
12. 前端 renderWithCitations 把 (第N页) 切成蓝色按钮
13. 点击 → PdfViewer iframe src 含 #search=<quote>&phrase=true&highlightAll=true
14. viewer.html 在 textlayerrendered + 2×rAF 后 eventBus.dispatch('find')
    PDFFindController 在指定页画黄色高亮
```

---

## 七、API 数据契约

### 7.1 上传

```http
POST /api/upload         multipart/form-data
  file: <pdf>
  ppt_config: '{"template":"academic_defense","page_count":12,...}'
  user_id: "alice"

200 → { session_id: uuid, status: "pending", space_id: "<hash>-<config>",
        cache_hit: false }
```

```http
POST /api/upload-multi   multipart/form-data
  files: <pdf1> <pdf2> ...
  ppt_config: ...
  user_id: ...
```

### 7.2 空间

```http
GET /api/users/{uid}/spaces
  200 → { spaces: [{space_id, paper_title, pdf_filename, session_type,
                    config, state, error_message, ready, created_at,
                    updated_at}, ...], count: N }

GET /api/spaces/{sid}?user_id=X
  200 → SpaceDetail（含 outputs.ppt_path/slides_dir/notes_dir）
        touch_access 副作用：updated_at + last_accessed_by[X]

DELETE /api/spaces/{sid}?user_id=X
  200 → { deleted: bool }     # 只删空间元数据 + 该用户会话目录

GET /api/spaces/{sid}/pdf                  → FileResponse PDF
GET /api/spaces/{sid}/pdf/{doc_id}         → 多文档某篇
GET /api/spaces/{sid}/slides               → { slides: [...], count }
GET /api/spaces/{sid}/slides/{filename}    → FileResponse SVG
GET /api/spaces/{sid}/ppt                  → FileResponse PPTX
GET /api/spaces/{sid}/script               → { slides: [{filename, content}] }
```

### 7.3 会话

```http
GET    /api/spaces/{sid}/conversations?user_id=X
       → { conversations: [{id, title, msg_count, created_at, updated_at}], count }

POST   /api/spaces/{sid}/conversations?user_id=X&title=...
       → ConversationDetail（含 messages=[]）

GET    /api/spaces/{sid}/conversations/{cid}?user_id=X
       → ConversationDetail

PATCH  /api/spaces/{sid}/conversations/{cid}?user_id=X&title=新标题
       → ConversationItem

DELETE /api/spaces/{sid}/conversations/{cid}?user_id=X
       → { deleted: bool }
```

### 7.4 问答

```http
POST /api/chat   application/json
  { session_id?, space_id?, conversation_id?, user_id, question }

200 → {
  answer: "...含 (第N页)，已剥离 <CITATIONS>",
  sources: [
    { chunk_id: 1, text: "preview...", file: "...", page: 6,
      doc_id: "doc_001", doc_order: 1, source_file_name: "M+.pdf",
      quote: "M+ outperforms all baselines",
    },
    ...
  ],
  conversation_id: "...",
  conversation_title?: "M+ 实验结果"      # 仅首问后才有
}
```

### 7.5 WebSocket

```
WS /ws/<task_id>
< { event: "progress", task: "ppt"|"rag", step, pct, stage, stage_label, progress_pct, status }
< { event: "log",      ts, source, level, stage, message, details }
< { event: "done",     status: "ready" }
< { event: "error",    message, source, stage, stdout_tail, stderr_tail }
< { event: "status",   ...SessionState snapshot }
```

---

## 八、关键设计决策

### 8.1 为什么 space_id = PPT cache_key

把"知识空间"和"PPT/RAG 缓存键"统一成同一个字符串，**空间元数据 + 产物存放天然对齐**。这样：
- 任何用户访问 space_id 时直接拼路径取产物，不需要查映射表
- 即便后端进程重启、内存里没有 session，spaces.py 仍能从硬盘读出全部产物

代价：换配置会生成新 space。但这就是"我换了模板要重做一份 PPT"的合理语义，且旧版仍保留在历史里。

### 8.2 为什么 session_store 用 in-process dict

- 任务进度推送、stage 状态频繁更新，落盘开销大
- task_id UUID 短期价值高，跑完任务后内存里也没人在乎
- 持久化的部分（产物路径、配置）都已通过 space_store / cache manifest 落到磁盘
- 进程重启的 fallback 通过 spaces.py + chat 的 `_resolve_retrieval` 解决

### 8.3 为什么用查询规划器（Haiku）

裸 RAG 在多文档场景下检索很容易被某一篇压制（哪篇的"创新点"段落更密，召回就全偏过去）。三种修法：

| 方法 | 准确性 | 延迟 | 复杂度 |
|---|---|---|---|
| 硬均衡（每篇强制各拿 N 个） | 单篇问题误伤 | 0 | 简单 |
| 关键词规则路由 | 漏检率高 | 0 | 简单 |
| **LLM 查询规划** | 高 | +3-4s | 中 |

选 Haiku 做规划：
- 单文档 space 直接跳过，无成本
- 多文档场景额外 3–4s，对总耗时 12–20s 来说占比可接受
- 准确度明显高于规则

### 8.4 为什么 verbatim quote + PDF.js 短语高亮

引用机制有多个候选：

| 方案 | 优点 | 缺点 |
|---|---|---|
| 仅页码 | 简单 | 用户还要自己找句子 |
| 句子级 ID + 后端高亮 | 完美对齐 | 需要重做 PDF 渲染 |
| **LLM 输出 verbatim quote + PDF.js phrase search** | 零额外渲染 | LLM 偶尔写错字符 |

我们采用第三种，配合 `_normalize_quote` 自动截到稳定子串 + 自定义 viewer 在 textlayerrendered 后才触发查找，命中率经测试 6/7 - 11/11 区间。

### 8.5 为什么 cache_version `v7` / `multi-v2`

每次 RAG 索引格式变化（如这次加了 bm25_corpus.json）就 bump 一次，旧目录自动失效。这比把所有旧索引手动迁移到新格式简单可靠。

### 8.6 为什么 task_manager 在 Claude CLI 报错时还能恢复

Claude CLI 在 Windows 偶尔会在最后一步把 bash 命令字符串当路径触发 `WinError 3`，但产物已全部落盘。`_ppt_task` catch 异常后：
1. `_find_latest_project(cache_dir)` 找最新项目
2. `_project_artifact_state` 检查 svg_final / notes 拆分 / pptx 都齐
3. 齐了就当成功，记 WARNING 日志继续走
4. 真不齐才往上抛

避免"产物明明在，却被假错误标失败"。

---

## 九、运行时数据流速参考（实测）

| 操作 | 耗时 |
|---|---|
| Hybrid retrieve（稳态） | ~0.7s |
| Reranker (CPU, bge-reranker-base, top 15 → top 6) | ~1-3s |
| Reranker (CPU, bge-reranker-v2-m3, top 15 → top 6) | ~5-10s |
| Query planner (Haiku, 多文档) | ~3-4s |
| Sonnet 4.6 答题（1500 tokens） | ~8-15s |
| 端到端单次问答（单文档） | ~10-18s |
| 端到端单次问答（多文档含规划） | ~13-22s |
| BGE-m3 索引构建（16 页论文，CPU） | ~5-8 分钟（首次模型加载占大头） |
| PPT 生成（单篇，Claude CLI） | ~4-8 分钟 |
| PPT 生成（多篇综述） | ~8-15 分钟 |

---

## 十、已知限制 & 未来扩展

### 当前限制

- PPT 生成依赖本地 `claude` CLI 可执行；服务器部署时需保证已安装并登录
- RAG 不支持表格 / 公式语义检索，pypdf 文本抽取对扫描件无能为力
- 多文档上限实际由 LLM 上下文窗口约束（10 篇以内问题不大）
- 引用 quote 高亮在含特殊符号时会自动截断到稳定子串，可能短于答案里实际引用
- 单进程：所有任务 / 会话 / WebSocket 都在一个 uvicorn 进程，多机部署需要外挂状态共享

### 已规划（v2）

教学讲义 → 教学 PPT：复用 ppt-master 已有的 docx/markdown 输入能力，加 scene 字段切换 prompt 模板（学习目标 / 知识点 / 例题 / 课堂练习 / 小结）。预计 2 个工作日实现。
