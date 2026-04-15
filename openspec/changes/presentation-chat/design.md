## Context

前端 `PptViewerPage` 已实现 PPTX 渲染和翻页。后端 session 中有 `rag_index_path`（目前为 stub 路径）。需要在不破坏已有 PPT 展示逻辑的前提下，将页面扩展为左右布局并接入问答。

## Goals / Non-Goals

**Goals:**
- 左右分栏：左侧 PPT（约 60% 宽），右侧对话框（约 40% 宽）
- `POST /api/chat` 接收问题，返回 `{ answer, sources }`
- DEV_MODE：直接读 fixture `design_spec.md` 作为上下文传给 LLM，跳过向量检索
- sources 每条包含 `text`（原文片段）、`file`（文件名）、`page`（页码，stub 返回 null）

**Non-Goals:**
- 真实向量检索（v2 实现，本变更只做 stub）
- 语音输入输出
- 多轮对话记忆（每次问答独立）
- 流式输出（先做同步响应）

## Decisions

### 决策 1：RAG stub — 直接用 design_spec.md 内容
DEV_MODE 下把 `fixture/design_spec.md` 全文作为 context 塞给 LLM。
真实模式下 RAG 返回空 context，LLM 仅凭问题回答。
这样不需要向量数据库就能跑通完整链路。

### 决策 2：LLM — Claude claude-haiku-4-5-20251001（同步）
用 `anthropic` SDK，`messages.create`（非流式）。
系统 prompt 告知模型它是一个文献阅读助手，context 是检索到的相关片段。

### 决策 3：前端布局 — CSS Grid 左右固定比例
`grid-cols-[3fr_2fr]`，左侧 PPT 面板，右侧对话框面板。
小屏（< 768px）自动堆叠为上下（`md:grid-cols-[3fr_2fr]`）。

### 决策 4：对话历史 — 前端 useState，不持久化
messages 数组存在 React state，刷新即清空。v1 足够。

### 决策 5：sources 展示 — 可折叠引用卡片
每条回答下方展示 sources 折叠面板，点击展开查看原文片段。
页码为 null 时显示"—"。

## Risks / Trade-offs

- [DEV_MODE context 长度] design_spec.md 可能超过 token 限制 → 截取前 4000 字符
- [无流式输出] 较长回答时用户等待感强 → v1 接受，加 loading spinner
- [CORS/proxy] chat 接口走 Vite 代理，与其他接口一致，无需额外配置

## Migration Plan

1. `pip install anthropic` 并在 `.env` 中加 `ANTHROPIC_API_KEY=...`
2. 新建 `backend/app/api/chat.py` 和 `backend/app/services/rag.py`
3. 修改 `backend/main.py` 注册 chat 路由
4. 修改前端 `PptViewerPage.tsx` 为左右布局

## Open Questions

- `ANTHROPIC_API_KEY` 由用户自行配置，不提交到代码库
