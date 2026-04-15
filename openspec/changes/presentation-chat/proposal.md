## Why

PPT 展示页目前是独立全屏页面，没有问答能力。用户需要在看 PPT 的同时能针对论文提问、获得 LLM 回答并定位到原文，这是文献阅读 Agent 的核心交互场景。

## What Changes

- 前端 `/session/:id/ppt` 页面改为左右布局：左边 PPT 翻页展示，右边文字问答对话框
- 后端新增 `POST /api/chat`：接收 session_id + question，RAG 检索 + LLM 回答，返回 answer 和 sources（含原文片段、文献名、页码）
- DEV_MODE 下 RAG 使用 fixture 的 `design_spec.md` 内容作为知识库，跳过真实向量检索
- LLM 调用使用 Claude API（`claude-haiku-4-5-20251001`）

## Capabilities

### New Capabilities

- `chat-api`: 后端问答接口，RAG 检索 + Claude LLM 回答，返回结构化 sources
- `presentation-layout`: 前端左右分栏布局，PPT 展示 + 问答对话框集成在同一页面

### Modified Capabilities

- `ppt-viewer`: 从全屏独立页面改为左侧半屏面板，支持翻页和下载

## Impact

- 新增后端依赖：`anthropic`（Claude SDK）
- 新增环境变量：`ANTHROPIC_API_KEY`
- 修改前端页面：`PptViewerPage.tsx` → 左右布局
- 新增后端路由：`backend/app/api/chat.py`
