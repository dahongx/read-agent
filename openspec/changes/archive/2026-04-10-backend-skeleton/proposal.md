## Why

文献阅读 Agent v1.0 需要一个 FastAPI 后端作为整个系统的骨架：接收 PDF 上传、管理异步任务（PPT 生成 + RAG 建索引）、提供 WebSocket 通道，同时支持 DEV_MODE 跳过 PPT 生成直接复用已验证结果，降低开发测试成本。

## What Changes

- 新建 `backend/` 目录，包含完整 FastAPI 项目结构
- `POST /api/upload` 接收 PDF，触发后台异步任务
- 异步任务管理器协调两条并行链路：PPT 生成 + RAG 建索引
- DEV_MODE（`.env` 配置）：跳过 PPT 生成，复用 `projects/M_plus_MemoryLLM_ppt169_20260409/` 已有结果；fixture 不完整时强制报错，禁止静默跳过
- WebSocket `/ws/{session_id}` 推送任务进度
- `GET /api/sessions/{id}` 查询当前会话状态

## Capabilities

### New Capabilities

- `pdf-upload`: 接收 PDF 文件上传，校验格式，创建 session，返回 session_id
- `task-manager`: 异步任务调度，协调 PPT 生成与 RAG 建索引两条并行链路，汇报进度
- `dev-mode`: DEV_MODE flag 控制，fixture 完整性校验，跳过或强制报错
- `session-state`: session 状态存储与查询（内存 dict，v1 不做持久化）
- `websocket-progress`: WebSocket 连接管理，向前端推送任务进度事件

### Modified Capabilities

（无已有 spec）

## Impact

- 新增依赖：`fastapi`, `uvicorn`, `python-multipart`, `python-dotenv`, `aiofiles`
- 目录结构：`backend/app/`, `backend/app/api/`, `backend/app/core/`, `backend/app/services/`
- 其他模块（PPT 生成、RAG、TTS）作为 service 后续挂载到此骨架
