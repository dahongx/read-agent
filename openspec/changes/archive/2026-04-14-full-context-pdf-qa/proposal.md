## Why

当前 RAG 检索存在两个根本性缺陷：
1. **检索质量差**：top-k chunk 切片导致上下文碎片化，"这篇文章说了什么"这类全局性问题无法得到准确回答
2. **来源定位无意义**：展示 chunk 文字片段不等于"定位原文"；用户需要的是能在完整 PDF 里看到上下文的引用

新方案：
- **废弃 RAG 检索**，改用全文上下文（Full-Document Context）：论文全文约 17K tokens，GLM-4-Flash 支持 128K context，直接发全文比检索片段更准确
- **行内页码引用**：要求 LLM 在回答中用 `(第N页)` 标注来源，前端将其解析为可点击链接
- **嵌入式 PDF 阅读器**：点击引用链接，在当前页面内弹出 PDF 预览并自动定位到对应页

## What Changes

- **Backend `app/api/chat.py`**：用 `get_full_context()` 替换 `retrieve()`；更新 system prompt 要求行内标注 `(第N页)`；从答案中解析页码引用生成 sources 列表
- **Backend `app/services/full_context.py`**（新建）：从已有 RAG index 读取所有 chunks，按页排序拼接为带页码标注的全文
- **Frontend `PdfViewer.tsx`**（新建）：iframe 模态框，接受 `sessionId` + `page` 参数，渲染浏览器内置 PDF 阅读器并定位到指定页
- **Frontend `ChatPanel.tsx`**：解析回答文本中的 `(第N页)` 模式，渲染为可点击 badge；点击打开 PdfViewer

## Capabilities

### New Capabilities
- `full-context-qa`: 全文上下文问答 + 行内页码引用解析
- `pdf-viewer`: 嵌入式 PDF 阅读器（iframe modal）

### Modified Capabilities
- `session-state`: 无变更（pdf_path 已存储，直接复用）

## Impact

- **Backend**：`app/api/chat.py` 大幅修改；新增 `app/services/full_context.py`；`app/services/rag.py` 不再被 chat 调用（可保留供将来使用）
- **Frontend**：`ChatPanel.tsx` 修改答案渲染逻辑；新增 `PdfViewer.tsx`；`PptViewerPage.tsx` 不变
- **Dependencies**：无新增依赖（pypdf 已安装；browser iframe 原生支持）
- **Fallback**：如果全文过长（> 80K tokens），自动降级到 top-16 RAG 检索
