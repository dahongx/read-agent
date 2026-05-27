# PPT 制作 Agent

通用 PPT 制作 + 内容问答 Agent。上传一个或多个文档（PDF），自动生成可演讲的 PPT、逐页讲稿，并提供基于原文的问答与高亮跳转。

支持 4 类内容场景，**模板和场景可自由组合**：

- **学术汇报**：论文/研究展示，强调结构、引用、数据
- **商务简报**：业务报告/数据汇报，结论优先
- **技术分享**：技术讲解/产品发布
- **教学讲义**：教师上课用的课件，按"导入 → 学习目标 → 新知讲解 → 例题 → 课堂练习 → 总结 → 作业"组织，speaker notes 第一人称课堂口吻 + 节奏标记 `[提问] [停顿] [板书]`

主流程：

```
上传 PDF → 选择模板 / 内容场景 → 生成 PPT + 讲稿 → 展示幻灯片 → 内容问答 → 原文页码跳转 + 短句高亮
```

## 当前能力

- 上传单个或多个 PDF，按"知识空间"组织
- 调用 Claude CLI 执行 `ppt-master` skill 生成 PPT（含 PDF→Markdown、图片抽取、SVG 排版、PPTX 导出）
- 8 套版式模板（学术答辩 / Anthropic / Google / 麦肯锡 / Exhibit / 活力红橙 / 重庆大学 / 自由设计）
- 4 类内容场景，教学讲义场景的 prompt + speaker notes 完全独立
- 输出 SVG 幻灯片、PPTX 文件、逐页讲稿
- 用户名隔离 + 历史空间复用：同样 PDF + 同样配置的 PPT/RAG 跨用户共享，对话历史按用户隔离
- 多会话管理（每空间最多 50 个对话，自动起标题）
- 基于内容的问答：BGE-m3 dense + BM25 hybrid 检索 + RRF 融合，可选 reranker
- 多文件场景智能查询路由（Haiku 决定按主题切片或单篇深入）
- 回答内带 `(第N页)` 引用：点击弹出 PDF 查看器、跳到对应页、PDF.js phrase search 高亮原文
- 浏览器 TTS 连续播报讲稿（教学场景自动跳过节奏标记和"要点：/时长：" 等元信息）
- Windows / Linux 跨平台：所有缓存路径用相对存储，git clone 到任意机器即可使用

## 项目结构

- `backend/` FastAPI 后端、任务编排、RAG、PPT 生成接入
- `frontend/` React + Vite 前端（开发模式 5173 / 生产托管 8000）
- `.claude/skills/ppt-master/` 通用 PPT 生成 skill（多 20+ 个模板，PDF/DOCX/Markdown/URL → SVG → PPTX）
- `openspec/` 需求与迭代记录

## 运行前准备

- Python 3.10+
- Node.js 18+
- Claude Code CLI（本机能直接跑 `claude` 命令）
- 可用的 LLM API Key（OpenAI 兼容协议；推荐 Claude Sonnet 4.6 / Haiku 4.5）

## 配置

1. 复制 `backend/.env.example` 为 `backend/.env`
2. 按实际环境填写关键变量：

- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` —— 答题主模型
- `LLM_PLANNER_MODEL` —— 多文件场景查询规划模型（推荐 Haiku，省钱快）
- `EMBED_MODEL_DIR` —— 本地 BGE-m3 路径
- `RERANKER_ENABLED` —— CPU 默认关闭，有 GPU 可开
- `SKILL_DIR` —— 默认 `.claude/skills/ppt-master`
- `CLAUDE_CLI_PATH` —— `claude` 不在 PATH 时显式指定
- `GIT_BASH_PATH` —— Windows 下 Claude CLI 需 Git Bash 时填

默认相对路径：

- `SKILL_DIR=.claude/skills/ppt-master`
- `UPLOAD_DIR=backend/uploads`
- `PPT_CACHE_DIR=backend/uploads/cache/ppt`

## 启动方式

### 生产模式

```bat
cd backend
start_prod.bat
```

会自动 `npm install + npm run build` 前端，启动 FastAPI 同时托管前端静态页面。

访问 `http://localhost:8000`。

### 开发模式

两个终端分别开：

```bat
cd backend
start.bat
```

```bat
cd frontend
npm run dev
```

后端 `8000`，前端 dev server `5173`。**改前端代码自动热更新**，访问 `http://localhost:5173`。

> 后端 `--host 0.0.0.0` 监听所有网卡，所以同 WiFi 设备也可以用 `http://你的IP:8000` 访问。

### 终端调试 RAG 问答

不开前端调 RAG：

```bat
cd backend
python chat_cli.py --pdf path/to/paper.pdf
```

参数：

- `--pdf <path>` 首次会建索引到 `backend/uploads/cache/rag/<sha>-cli/`
- `--index <dir>` 复用已有索引目录（必须已含 `bm25_corpus.json`）
- `--question "..."` 单次问答，不进交互
- `--quiet` 抑制 INFO 日志

输出每条问答的答案、`<CITATIONS>` 里的逐字 quote、quote 是否命中检索 chunk、retrieve / LLM 各自耗时。

## 数据持久化与缓存

所有运行时数据存放在 `backend/uploads/` 下，按目录分层：

```
backend/uploads/
├── spaces/<space_id>.json              知识空间元数据（PDF + 配置 + 状态）
├── cache/
│   ├── ppt/<space_id>/                 PPT 产物（svg_final/、notes/、*.pptx）
│   └── rag/<pdf_hash>-v7/              向量索引（含 BM25 corpus）
├── conversations/<user_id>/<space_id>/ 用户对话历史
└── sessions/<task_id>/                 上传文件 + 任务日志
```

**关键设计**：所有路径用**相对路径**存储（相对仓库根），跨机器迁移不需要改任何文件——直接 git pull 到服务器就能用。

## 内置示例

仓库内置 3 个示例知识空间（用户名 `123`）：

- `d26f7eb599540e8b-b5a08452` 单文件论文示例
- `5fafbc5d7f062de6-b5a08452-86e9e44e` 多文件综述示例
- `fd3d2aa62172006d-5c0e76b6` 教学讲义示例（量子力学第四讲）

git clone 后用 `123` 登录就能直接看到这些空间，无需重新生成。

## 部署到服务器

`backend/scripts/migrate_legacy_cache.py` 可以一次性把任何旧的绝对路径数据修复成相对路径（包括 `space.json`、`project_manifest.json`）。已内置示例数据已经修好。

部署流程极简：

1. 服务器上准备 Python / Node / Claude CLI
2. `git clone` 仓库
3. `pip install -r backend/requirements.txt`
4. `cd frontend && npm install && npm run build`
5. 配置 `backend/.env`（最小：`LLM_API_KEY`）
6. `start_prod.bat` 等价于 Linux 上 `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000`

模型缓存（BGE-m3 ~2GB）首次启动会从 HuggingFace 下载；服务器在国内访问 HF 不通时，本地把 `backend/models/bge-m3/` 整个目录 scp 过去即可。

## 发布说明

`.gitignore` 已经忽略：

- `backend/.env`（密钥）
- `backend/uploads/`（绝大部分），但**精确放行 3 个示例空间的所有产物**
- `backend/models/`（嵌入模型，太大不进 git）
- `frontend/node_modules/` / `frontend/dist/`
- `projects/` / `output/` / `paper/`（早期废弃目录）
