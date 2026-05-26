# 多篇论文上传生成 PPT / RAG 方案（综述模式）

## Context
当前项目主链路是“单篇 PDF 上传 → 并行生成 PPT 与 RAG → session ready”。现在要在**不破坏现有单篇链路**的前提下，新增 **多篇综述** 模式：用户可上传多篇论文，最终生成一个综述 PPT，并同时构建一个支持后续问答的多文献联合 RAG 索引。

本次范围已经收敛为：
- **只做多篇综述**，不做对比模式
- 前端只新增一个模式切换：`单篇` / `多篇综述`
- 其它 PPT 配置项继续沿用单篇当前页面，不新增主题 / 听众 / 重点等额外输入
- multi 模式下最终仍然要有 **PPT + RAG**，但实现上拆成两条路：
  - **PPT 路**：先完成，多 PDF → 多 MD → merged.md → 综述 PPT
  - **RAG 路**：随后完成，多 PDF 原文抽取 → 多文献联合索引

## 关键设计结论

### 1. 两条路并行于同一 session，但输入组织不同
**PPT 路**：
- 使用 `ppt-master` 的 Markdown 体系
- 多 PDF 分别转 Markdown
- 合并为 `merged.md`
- 生成一个综述 PPT

**RAG 路**：
- 不依赖 `merged.md`
- 直接以每篇 PDF 原文为输入进行抽取、切块、向量化
- 最终写入一个 **session 级联合索引**
- 每个 chunk 带来源元数据，用于后续问答定位“来自哪一篇文章”

结论：**PPT 用 markdown 体系，RAG 用 PDF 原文体系**。这两条链路共享同一批输入文件和同一个 session，但不要强耦合成一条处理链。

### 2. `doc_id` 的作用
`doc_id` 不是为了检索命中，而是为了：
- 在联合索引里给每篇文献一个稳定身份
- 让每个 chunk 都能明确归属于某篇文献
- 后续问答时能稳定返回引用来源
- 避免直接依赖文件名作为索引内部主键

推荐形式：
- `doc_001`
- `doc_002`
- `doc_003`

注意：
- **向量检索仍然按内容 embedding 命中**，不是按 `doc_id` 命中
- `doc_id` 只是索引 metadata 中的“来源主键”

### 3. RAG 缓存应基于内容，不应依赖文件名
多篇联合索引的缓存键应包含：
- 各 PDF 的**内容 hash**
- 文件顺序
- RAG version
- embedding model
- chunk 参数

因此：
- **同一篇文章换个文件名，只要内容一样，应当命中同一个 RAG 缓存**
- 文件名只作为展示信息 / 来源标签，不应参与缓存主键

建议：
- `doc_id` 用于 session 内部身份标识
- `source_file_name` 用于展示
- `content_hash` 用于缓存与去重判断

## 总体策略
不要改坏现有单文件 API 和 `run_tasks(session_id, pdf_path, config)` 语义。新增 multi 分支：
- 新增上传接口：`backend/app/api/upload.py`
- 新增多篇任务编排：`backend/app/services/task_manager.py`
- 新增多文献 PPT 生成入口：`backend/app/services/ppt_generator.py`
- 新增多文献联合索引入口：`backend/app/services/rag_index.py`
- 扩展 session model 为 `single | multi`
- 前端上传页增加“多篇综述”模式，但保留现有单篇默认体验

这样可以保证：
- 当前单篇主链路零破坏
- 回归风险局限在 multi 分支
- 后续问答能力可直接复用 multi RAG 索引

---

## 一、PPT 路设计（先实现）

### 1. 核心流程
1. 用户上传多个 PDF
2. 后端为 session 归档所有 PDF，并写入 `input_files`
3. 创建 multi project 目录
4. 调用 `ppt-master` 的 `project_manager.py import-sources <project> <pdf1> <pdf2> ...`
   - 复用其现有多 source 导入能力
   - 让每篇 PDF 自动转成独立 Markdown
   - 保留各自 companion asset 目录
5. 后端扫描导入后的多个 Markdown，按固定顺序生成 `sources/merged.md`
6. prompt 明确告诉 `ppt-master`：本次为多篇论文综述 PPT，应基于 merged 内容做统一综述，而不是逐篇孤立生成
7. 按现有 batch mode 继续跑完整条 PPT 流程，直到 `svg_final/` 与 PPTX 导出

### 2. 为什么 PPT 路继续采用“先分别转 MD，再 merge”
这是和现有 skill 架构最一致、改动最小的路线：
- `ppt-master` 本身就是 source → markdown(+assets) → design/executor/export 的体系
- `project_manager.py import_sources()` 已支持一次导入多个 source item
- `pdf_to_md.py` 已为每篇文档产出独立 `<md_stem>_files/` 目录
- 图片、表格、正文提取逻辑已存在，无需重写多 PDF 解析
- merge 只发生在 Markdown 层，工程复杂度远低于直接让现有单篇 prompt 同时理解多个 PDF 原件

### 3. 图片处理策略
结论：**可以复用现有 skill 的图片处理能力，但 merge 时必须保住相对路径。**

已存在的可复用能力：
- `pdf_to_md.py`：每篇 PDF 转出的 Markdown 会引用自己的 `<stem>_files/` 目录
- `project_manager.py`：导入 source 时已考虑中间产物与资源归档
- `finalize_svg.py`：后处理阶段会根据 SVG 中已写入的图片引用做 embed/crop/fix，不关心图片来自哪一篇 PDF

落地规则：
- `merged.md` 写在与各篇 Markdown 同级的位置（通常 `sources/`）
- 合并时直接引用原 Markdown 内容，不要把图片文件平铺重命名后再二次改写
- 若 merge 脚本改写路径，必须保持相对 `merged.md` 可解析
- 导入阶段应保证每个输入文件有稳定且唯一的归档名，避免 `_files` 目录冲突

### 4. merge 内容组织建议
`merged.md` 不建议“裸拼接”，而应加入轻量结构，帮助后续 LLM 产出综述型 PPT。建议格式：

```md
# 多篇论文综述资料

## 文献 1：<标题或文件名>
- source_file: <original filename>
- order: 1

<该论文 markdown 正文>

---

## 文献 2：<标题或文件名>
- source_file: <original filename>
- order: 2

<该论文 markdown 正文>
```

约束：
- 保留每篇文献分隔头
- 保留来源文件名 / 顺序编号
- 不在 merge 阶段做过强总结，尽量保留原始材料

### 5. PPT 缓存设计
`compute_multi_cache_key(pdf_paths, config)` 建议包含：
- 所有 PDF 内容 hash（按稳定顺序）
- 文件顺序
- PPT config
- merge strategy version

注意：
- **缓存应按内容，不按文件名**
- 同内容不同文件名，理论上应命中相同 PPT 缓存

---

## 二、RAG 路设计（PPT 路完成后实现）

### 1. 核心原则
multi 模式下的 RAG 不是“把多个 PDF 拼成一个大文本再切块”，而是：
- 每篇 PDF 分别抽取文本
- 每篇分别切块
- 每个 chunk 打上来源 metadata
- 最后统一写入一个 **session 级联合索引**

也就是逻辑上：

```text
pdf1 -> chunks(with doc_001 metadata)
pdf2 -> chunks(with doc_002 metadata)
pdf3 -> chunks(with doc_003 metadata)
--> merge into one vector store
```

而不是：

```text
pdf1 + pdf2 + pdf3 -> one big text -> chunks
```

后者会丢失来源边界，不利于后续问答定位引用。

### 2. 为什么 RAG 路优先基于 PDF 原文而不是 merged.md
推荐路线：**RAG 继续按每篇 PDF 原文抽取，再统一入一个 session 索引。**

原因：
- RAG 的目标是问答与引用定位，不是生成 PPT
- PDF 原始页码对于问答引用很重要
- 后续回答“这段来自哪篇文章第几页”时更稳
- 不会受 `merged.md` 组织方式影响

### 3. 联合索引 metadata 设计
每个 chunk 至少带这些字段：

```json
{
  "session_id": "xxx",
  "session_type": "multi",
  "doc_id": "doc_001",
  "doc_order": 1,
  "source_file_name": "paper_a.pdf",
  "content_hash": "...",
  "page_num": 5,
  "chunk_id": "doc_001_chunk_00012"
}
```

如果后续抽取得到更多信息，可继续补充：
- `paper_title`
- `section_title`
- `content_type`

第一版最低要求：
- `doc_id`
- `doc_order`
- `source_file_name`
- `content_hash`
- `page_num`
- `chunk_id`

### 4. doc_id / 文件名 / 内容 hash 的职责分离
建议职责如下：
- `doc_id`：session 内部稳定身份标识，用于索引 metadata 和引用归属
- `source_file_name`：展示给前端 / 用户看的原始来源名
- `content_hash`：缓存命中、去重判断、来源一致性判断

这三者不要混用。

### 5. 多篇联合索引缓存设计
联合索引 cache key 建议包含：
- 各 PDF 内容 hash
- 文件顺序
- chunk 参数
- embed model
- rag version

因此：
- **同一篇文章用不同文件名上传，只要内容相同，应命中同一份 RAG 缓存**
- 如果上传顺序不同，可视为不同 session 语义，建议纳入缓存键

### 6. 后续问答引用能力的准备
检索结果至少要能返回：
- `doc_id`
- `source_file_name`
- `page_num`
- `snippet`
- `score`

这样后续问答时可以明确回答：
- 这段内容来自哪篇文章
- 来自第几页
- 若多篇都提到，可分别列出来源

---

## 三、数据模型与接口调整

### 1. 后端模型
关键文件：`backend/app/models.py`

建议扩展：
- `session_type: Literal["single", "multi"]`
- `pdf_path` 保留给 single 使用
- `input_files` 继续作为 multi 的标准输入列表
- 新增：
  - `merged_markdown_path: Optional[str]`
  - `source_count: int = 1`
  - `source_documents: list[SessionSourceDoc] = []`

建议新增结构：

```python
class SessionSourceDoc(BaseModel):
    doc_id: str
    order: int
    source_file_name: str
    pdf_path: str
    content_hash: str
    markdown_path: str | None = None
```

### 2. session store
关键文件：`backend/app/services/session_store.py`

复用 / 扩展：
- 继续复用 `set_input_files()`
- 保留 `set_pdf_path()` 给 single
- 新增：
  - `set_session_type()`
  - `set_source_documents()`
  - `set_merged_markdown_path()`

### 3. 上传接口
关键文件：`backend/app/api/upload.py`

建议：
- 保留现有 `/api/upload` 完全不动，继续单文件
- 新增 `/api/upload-multi`
- 参数：
  - `files: list[UploadFile]`
  - `ppt_config`
- 校验：
  - 至少 2 个 PDF
  - 每个文件都必须是 `.pdf`
- 创建 multi session
- 保存所有上传文件
- 为每篇生成 `content_hash`
- 写入 `input_files` + `source_documents`
- 启动新的 multi 任务入口，而不是复用现有 `run_tasks(session_id, pdf_path, config)`

---

## 四、任务编排调整
关键文件：`backend/app/services/task_manager.py`

建议新增：
- `async def run_multi_tasks(session_id: str, pdf_paths: list[str], config: PptConfig | None = None) -> None`
- `async def _multi_ppt_task(session_id: str, pdf_paths: list[str], config: PptConfig) -> str`
- `async def _multi_rag_task(session_id: str, pdf_paths: list[str]) -> str`

编排原则：
- single：仍使用现有 `run_tasks()`，保持 PPT + RAG 并行
- multi：最终也保持 PPT + RAG 并行，但开发顺序上先完成 PPT 路，再接入 RAG 路
- 进度广播继续沿用 `_broadcast_progress()` / `_broadcast_session_snapshot()` / `_log()`

建议 multi 阶段定义：
- `archive_sources`
- `import_sources`
- `merge_markdown`
- `ppt_generation`
- `rag_parse`
- `rag_embedding`
- `complete`

---

## 五、服务层改造

### 1. `backend/app/services/ppt_generator.py`
保留现有单文献接口，并新增：
- `compute_multi_cache_key(pdf_paths: list[str], config: PptConfig) -> str`
- `prepare_multi_project_sources(...) -> tuple[Path, Path]`
- `run_multi_ppt_generation(session_id, pdf_paths, config, cache_dir, progress_cb, log_recorder) -> Path`

### 2. `backend/app/services/rag_index.py`
新增多文献入口，例如：
- `build_multi_index(source_docs: list[SourceDoc], index_dir: str) -> None`

职责：
- 遍历每篇 PDF
- 提取文本
- 独立切块
- 给每个 chunk 附 metadata
- 统一写入同一个 `index_dir`

这是 multi RAG 的关键实现点。

---

## 六、前端改造建议
关键文件：`frontend/src/pages/UploadPage.tsx`

建议采取最小侵入式 UI：
- 保留当前单文件上传为默认模式
- 增加模式切换：
  - 单篇
  - 多篇综述
- 单篇模式继续当前 `selectedFile`
- 多篇模式使用 `selectedFiles: File[]`
- 其它 PPT 配置完全沿用现有单篇表单
- 提交到新接口 `/api/upload-multi`

这样可以确保：
- 用户学习成本最低
- 单篇行为不变
- 多篇综述只比现在多一个模式切换

---

## 七、会话与下载展示
关键文件：
- `backend/app/api/sessions.py`
- 前端 session detail 相关组件

建议：
- 保留当前 `/api/sessions/{session_id}/pdf` 仅服务 single
- multi 不强行复用该接口返回某一个 PDF
- session payload 中直接展示 `input_files` / `source_documents`
- 如有需要再新增：
  - `/api/sessions/{session_id}/sources`
  - `/api/sessions/{session_id}/merged-markdown`

---

## 关键复用点
- `backend/app/services/task_manager.py`
  - 复用 `_broadcast_progress()`
  - 复用 `_broadcast_session_snapshot()`
  - 复用 `_log()`
- `backend/app/services/session_store.py`
  - 复用 `set_input_files()`
- `backend/app/models.py`
  - 复用 `SessionFile`、`SessionState` 并扩展 `session_type`
- `.claude/skills/ppt-master/scripts/project_manager.py`
  - 复用 `import_sources()` 多源导入能力
- `.claude/skills/ppt-master/scripts/pdf_to_md.py`
  - 复用单篇 PDF → Markdown + `_files` 资源目录能力
- `.claude/skills/ppt-master/scripts/finalize_svg.py`
  - 复用后处理图片 embed 能力
- `backend/app/services/rag_index.py`
  - 复用现有单篇索引构建逻辑，抽出多文献公共能力

## 需要修改的关键文件
- `E:\agent\reading\read-agent\backend\app\models.py`
- `E:\agent\reading\read-agent\backend\app\services\session_store.py`
- `E:\agent\reading\read-agent\backend\app\api\upload.py`
- `E:\agent\reading\read-agent\backend\app\services\task_manager.py`
- `E:\agent\reading\read-agent\backend\app\services\ppt_generator.py`
- `E:\agent\reading\read-agent\backend\app\services\rag_index.py`
- `E:\agent\reading\read-agent\frontend\src\pages\UploadPage.tsx`
- `E:\agent\reading\read-agent\openspec\changes\frontend-upload-ppt\specs\pdf-upload-ui\spec.md`（或新增一条 multi-upload spec 变更）

## 实施顺序
1. 扩展 session/model/store，支持 `multi` 语义与 `source_documents`
2. 新增 `/api/upload-multi`，完成多文件落盘、content hash 计算与 session 创建
3. 在 `ppt_generator.py` 中实现多源导入 + `merged.md` 生成 + multi PPT cache（先完成 PPT 路）
4. 在 `task_manager.py` 中新增 multi PPT 任务编排与进度定义
5. 前端上传页增加“单篇 / 多篇综述”模式切换
6. 在 `rag_index.py` 中实现 `build_multi_index()`，完成多文献联合索引
7. 在 `task_manager.py` 中接入 multi RAG，并与 multi PPT 并行
8. 会话详情补充多 source 展示与后续问答引用所需字段
9. 补充 spec / README / PRD 对齐说明

## 验证方案

### A. 单篇上传回归
- 调用现有 `/api/upload`
- 验证仍进入 `run_tasks()`
- 验证 PPT 与 RAG 仍并行，ready/error 行为不变

### B. 多篇综述 PPT 验证
- 调用 `/api/upload-multi`，上传 2~3 个 PDF
- 验证 session 为 `multi`
- 验证 `input_files` / `source_documents` 正确记录
- 验证 project 下生成每篇 Markdown 与 `merged.md`
- 验证最终能生成 PPTX

### C. 多篇联合 RAG 验证
- 验证为每篇文献分配 `doc_id`
- 验证索引中每个 chunk 都带 metadata：`doc_id` / `source_file_name` / `page_num` / `chunk_id`
- 验证同内容不同文件名可命中相同 RAG 缓存
- 验证检索结果能区分不同来源文献

### D. 资源/图片验证
- 选择包含图片的 2 篇 PDF
- 检查各自 `_files` 目录是否存在
- 检查 `merged.md` 中图片相对路径是否仍可解析
- 检查最终 `svg_final/` 与导出的 PPTX 中图片是否正常显示

### E. 前端验证
- 单篇模式 UI 与提交流程保持原样
- 多篇模式支持选择多个 PDF
- 多篇 session 状态与进度展示正常
- 后续问答场景可利用 source metadata 展示引用来源

## 结论
推荐按“**新增 multi 分支；PPT 路继续复用 import-sources + pdf_to_md + merged.md；RAG 路单独基于 PDF 原文构建带来源元数据的联合索引**”的路线实施。这样既能保持单篇主链路稳定，又能真正支撑多篇综述后的问答引用定位能力。