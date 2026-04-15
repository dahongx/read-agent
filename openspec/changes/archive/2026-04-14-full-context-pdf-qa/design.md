## Context

**当前架构**：上传 PDF → `pypdf` 解析 → LlamaIndex 向量化 → 问答时 top-k 检索

**新架构**：上传 PDF → `pypdf` 解析 → 全文缓存（已有 docstore）→ 问答时发送全文

全文已存在于 RAG index 的 `docstore/data`（28 chunks，~70K chars，~17K tokens）。无需重新解析 PDF，直接从 docstore 读取并按页排序拼接即可。

## Goals / Non-Goals

**Goals:**
- 全文上下文问答，回答质量显著提升
- LLM 行内标注 `(第N页)`，前端解析为可点击 badge
- 点击 badge 弹出 PDF 阅读器并定位到对应页
- 超长文档自动降级到 RAG

**Non-Goals:**
- 语义高亮（PDF.js 文本层高亮）— 浏览器 iframe 无法编程控制
- 多文档场景实现（本期只做单文档，但接口设计需为两阶段扩展留口）
- 流式回答（streaming response）

## Decisions

**Decision 1: 从 docstore 读取全文，而非重新解析 PDF**
已经有 `rag_index_path` 存储了完整的 chunks + 页码 metadata。直接读 `docstore.json` 比重新调用 pypdf 更快，且 page_label 已提取完毕。

**Decision 2: 行内引用格式 `(第N页)` 而非结构化 JSON**
要求 LLM 输出结构化 JSON 会增加 prompt 复杂度和解析出错风险。行内 `(第N页)` 格式自然、可读，正则解析稳定。前端用 `/(第\d+页)/g` 分割答案文本。

**Decision 3: iframe 而非 react-pdf**
`react-pdf` 需要配置 PDF.js worker，增加 bundle size。浏览器内置 PDF viewer 通过 `<iframe src="url#page=N">` 即可定位，零依赖，Chrome/Edge 完整支持。

**Decision 4: 模态框而非侧边栏**
侧边栏会压缩问答区域。PDF 需要足够空间阅读，模态框（80% viewport）更合适，关闭后回到对话。

**Decision 5: 降级阈值 80K tokens**
glm-4-flash 支持 128K，留 48K 余量给 system prompt + 对话历史。实际学术论文通常 < 50K tokens，降级很少触发。

**Decision 6: 多论文扩展路径（本期不实现，接口预留）**
`get_full_context(session_id)` 返回的是单个 session 的全文。当未来支持多 session 联合问答时，调用方只需：
1. **阶段一（路由）**：对每个 session 的摘要做向量比较，选出 top-2 个最相关 session
2. **阶段二（全文）**：调用 `get_full_context()` 获取这 2 个 session 的全文，拼接后一起发给 LLM

单篇 → 多篇只需在调用层加路由逻辑，`get_full_context()` 本身不需要改。

## Risks / Trade-offs

- [Risk] 全文发送增加 API 成本（每次问答 ~17K tokens 输入）→ 对 GLM-4-Flash 成本影响极小（约 0.001 元/次）
- [Risk] `(第N页)` 解析误判——LLM 可能在答案中随意使用括号数字 → Mitigation: 只匹配 `(第\d{1,3}页)` 模式，页数在合理范围内
- [Risk] iframe PDF 定位在某些浏览器不支持 `#page=N` → Mitigation: 显示"第N页"文字说明，用户可手动翻页
- [Risk] docstore 不存在（DEV_MODE_RAG=true 跳过了建索引）→ Mitigation: fallback 读 design_spec.md（已有逻辑）
