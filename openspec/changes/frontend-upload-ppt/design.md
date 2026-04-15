## Context

后端已提供三个接口：`POST /api/upload`、`GET /api/sessions/{id}`、`WS /ws/{session_id}`。
前端从零开始，需要在 `frontend/` 目录下搭建 React 18 + Vite + TypeScript 项目，实现三个页面的核心流程。

## Goals / Non-Goals

**Goals:**
- 三页面路由：上传页 → 进度页 → PPT 展示页
- WebSocket 实时双进度条（PPT 生成 + RAG 建索引）
- PPTX 渲染（至少能翻页展示幻灯片）
- Vite 开发代理，统一转发 `/api` 和 `/ws` 到后端 `localhost:8000`

**Non-Goals:**
- 语音问答界面（下一个变更）
- 用户登录 / 多用户
- 移动端适配
- 生产环境部署配置

## Decisions

### 决策 1：路由方案 — React Router v6
使用 `react-router-dom` v6，三条路由：`/`（上传）、`/session/:id`（进度）、`/session/:id/ppt`（展示）。
替代方案：单页状态机（useState 切换视图）—— 拒绝，URL 可分享、可刷新更重要。

### 决策 2：WebSocket 管理 — 原生 + 自定义 Hook
`useWebSocket(sessionId)` 封装原生 WebSocket，返回 `{ events, status }`，组件订阅即可。
替代方案：`socket.io-client` —— 后端未用 socket.io，无需引入。

### 决策 3：PPT 渲染 — pptxjs（PPTX to HTML）
使用 `pptxjs` 或 `PPTXjs` 将 PPTX 转成 HTML 在浏览器渲染，支持翻页。
替代方案 A：Office 在线预览（需网络，隐私风险）—— 拒绝。
替代方案 B：iframe + blob URL（浏览器无法直接渲染 PPTX）—— 拒绝。
替代方案 C：后端转 PDF 再用 PDF.js —— 依赖后端，v1 暂不引入。
**备选**：若 pptxjs 渲染质量差，降级为"提供下载按钮 + 缩略图列表"。

### 决策 4：状态管理 — React Context + useReducer
进度状态通过 Context 传递，无需 Redux。三个页面之间数据量小，不需要全局状态库。

### 决策 5：样式 — Tailwind CSS
Vite 生态下安装简单，utility-first 适合快速原型。不引入 UI 组件库（减少依赖）。

### 决策 6：后端文件服务
PPT 文件当前存在 `backend/uploads/{session_id}/` 下，需要后端新增静态文件服务或下载路由（`GET /api/sessions/{id}/ppt`），前端通过该 URL 获取 PPTX 二进制。

## Risks / Trade-offs

- [pptxjs 渲染兼容性] 复杂 PPT 样式可能丢失 → 降级方案：显示下载链接
- [WebSocket 断线] 进度页刷新后 WS 重连，需重新拉取当前状态 → 连接后立即收到快照（后端已实现）
- [后端无文件下载接口] PPT 渲染依赖后端新增 `/api/sessions/{id}/ppt` 路由 → 作为本次任务一部分实现

## Migration Plan

1. 在 `frontend/` 下 `npm create vite@latest` 初始化项目
2. 安装依赖：`react-router-dom`, `tailwindcss`, `pptxjs`
3. 启动：`npm run dev`（Vite 默认 5173 端口，代理转发到后端 8000）
4. 后端同步新增 `GET /api/sessions/{id}/ppt` 文件下载路由

## Open Questions

- pptxjs 渲染效果需实测，若不满意在实现阶段切换降级方案
