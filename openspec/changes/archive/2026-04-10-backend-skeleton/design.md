## Context

文献阅读 Agent v1.0 需要一个 FastAPI 后端作为整个系统的骨架。当前没有任何后端代码，本变更从零搭建。

主要约束：
- v1 仅做内存状态（无数据库），便于快速迭代
- DEV_MODE 让开发者跳过耗时的 PPT 生成，直接复用已有 fixture，降低测试成本
- PPT 生成与 RAG 建索引两条链路互相独立，必须并行执行

## Goals / Non-Goals

**Goals:**
- 提供 `POST /api/upload` 接收 PDF，校验格式，返回 session_id
- 异步任务管理器并行驱动两条链路：PPT 生成 + RAG 建索引
- WebSocket `/ws/{session_id}` 向前端推送细粒度进度事件
- `GET /api/sessions/{id}` 查询 session 当前状态
- DEV_MODE：跳过 PPT 生成，复用 fixture；fixture 不完整时强制报错

**Non-Goals:**
- 持久化存储（数据库、Redis）—— v2 再做
- 用户认证 / 多租户
- PPT 生成、RAG、TTS 的具体算法实现（本变更只留接口桩）

## Decisions

### 决策 1：FastAPI + asyncio 原生异步
**选择**：使用 `asyncio.create_task` 驱动后台任务，不引入 Celery/RQ。
**理由**：v1 单进程足够，避免引入消息队列依赖；后续升级到 Celery 只需替换 task_manager 内部实现。

### 决策 2：内存 session 存储（dict）
**选择**：`Dict[str, SessionState]` 存在 `app.state` 中。
**理由**：v1 不需要持久化；进程重启 session 丢失可接受（开发阶段）。

### 决策 3：WebSocket 推送 vs. SSE vs. 轮询
**选择**：WebSocket。
**理由**：后续前端需要双向交互（语音问答），WebSocket 天然支持；SSE 只能单向。

### 决策 4：DEV_MODE fixture 路径硬编码
**选择**：DEV_MODE 时固定读取 `projects/M_plus_MemoryLLM_ppt169_20260409/`。
**理由**：v1 只有一组验证过的 fixture，无需通用化；fixture 缺失时主动报错而非静默跳过，防止假通过。

### 决策 5：目录结构
```
backend/
  app/
    api/          # 路由层
    core/         # 配置、启动
    services/     # 业务逻辑（task_manager, dev_mode, session_store）
    models.py     # Pydantic 模型
  main.py
  .env.example
```

## Risks / Trade-offs

- [内存 session 无持久化] → 进程崩溃后 session 全失；v1 接受，v2 加 Redis
- [单进程并发] → CPU 密集型任务（PPT 生成）会阻塞 event loop；现阶段 PPT 生成为桩函数，实际接入时需用 `run_in_executor`
- [DEV_MODE fixture 硬编码] → 换一组论文时需手动修改路径；v1 可接受，后续支持环境变量配置

## Migration Plan

1. 在 `backend/` 目录下新建所有文件
2. 安装依赖：`pip install fastapi uvicorn python-multipart python-dotenv aiofiles`
3. 启动：`uvicorn backend.main:app --reload`
4. DEV_MODE：复制 `.env.example` 为 `.env`，设置 `DEV_MODE=true`

## Open Questions

- WebSocket 断线重连策略（v1 暂不处理，客户端重连即可）
- session_id 生成方式：UUID4 足够，无需其他方案
