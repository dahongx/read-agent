## Why

后端 API 骨架已就绪，但用户没有任何可操作的界面。需要一个前端将"上传 PDF → 实时进度 → 查看 PPT"这条核心流程串通，让用户能端到端地体验文献阅读 Agent。

## What Changes

- 新建 `frontend/` 目录，基于 React 18 + Vite + TypeScript 搭建前端项目
- 上传页：拖拽 / 点击上传 PDF，调用 `POST /api/upload`，跳转到进度页
- 进度页：通过 WebSocket `/ws/{session_id}` 实时展示 PPT 生成和 RAG 建索引两条进度条，完成后自动跳转
- PPT 展示页：渲染生成的 PPTX 文件，支持翻页

## Capabilities

### New Capabilities

- `pdf-upload-ui`: 文件上传界面，拖拽/点击选择 PDF，调用后端上传接口，处理校验错误提示
- `progress-view`: 实时进度展示，WebSocket 订阅两条并行任务（PPT 生成 + RAG 建索引）的进度条和状态
- `ppt-viewer`: PPTX 文件渲染与翻页控制，通过后端提供的文件 URL 加载

### Modified Capabilities

（无）

## Impact

- 新增依赖：`react`, `react-dom`, `vite`, `typescript`, `react-router-dom`
- PPT 渲染库待选（见 design.md）
- 前端通过相对路径 `/api/...` 和 `/ws/...` 访问后端，开发时 Vite 代理到 `localhost:8000`
- 新增 `frontend/` 目录，与 `backend/` 并列
