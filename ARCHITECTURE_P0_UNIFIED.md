# ARCHITECTURE P0 UNIFIED — 实际问题复盘与当前收口方向

> 更新时间：2026-04-24  
> 当前结论：PPT 主链路已经阶段性跑通；现阶段不再继续扩展 PPT 范围，优先把经验沉淀清楚，并把问答链路重新对齐到“答案可回指论文原文”。

---

## 一、这份文档为什么要重写

旧版 `ARCHITECTURE_P0_UNIFIED.md` 更像一份早期“统一化大改造方案”，里面把很多事项写成待实现目标，但已经不能准确反映这轮真实发生的问题、已经完成的修复，以及下一步的工作重点。

这轮真实推进下来，最重要的经验并不是“先做一套抽象上完美的新架构”，而是：

1. **主链路必须先收敛**，否则排障时无法判断问题到底出在哪一层；
2. **产物定位策略必须一致**，否则会出现“实际上做了一半甚至基本成功，但系统却报失败”的假阴性；
3. **原始输入、缓存、正式产物必须职责分开**，否则 PPT 和 RAG 会互相干扰；
4. **进度与错误必须可观测**，否则用户只能看到“卡住了”，不知道是慢、挂了、还是已经有部分产物；
5. **平台差异必须前置约束**，尤其是 Windows 环境下不能默认沿用类 Unix 命令假设。

因此，这份文档改为记录：**这轮实际踩过的坑、根因、已完成修复、当前系统状态，以及下一步为什么应该转向 Q&A / RAG 原文定位。**

---

## 二、本轮实际目标与范围收敛

### 2.1 最初目标

最初目标是把论文到 PPT 的主流程真正跑通，且严格只使用 `/ppt-master`：

- 只走 `/ppt-master`
- 输出 10 页中文学术汇报
- 优先 anthropic 模板，不可用则自由设计
- 跑完整条链路直到 `svg_final` 和 `pptx`
- 每个阶段都能回报当前产物路径

### 2.2 中途为什么演变成系统修复

在真实运行中，问题并不只出在某个单点脚本，而是暴露出一整条链路的不一致：

- PPT 主入口不够纯，历史逻辑还在干扰判断；
- 正式产物目录、会话目录、缓存目录的职责边界不够清晰；
- 前端只能看到粗粒度进度，无法区分“正常慢”和“已经失败”；
- 后端错误语义不准确，掩盖了更早的真实失败原因；
- Windows 环境下技能调用默认假设 `python3` 存在，直接导致执行失败。

所以这轮工作实际上先完成了一个 **P0 级收口**：不是追求一次性做完所有统一架构，而是优先把 PPT 主链路修到“能跑、能看、能定位问题”。

### 2.3 当前范围已经再次收缩

用户随后已明确要求：

- **PPT 暂时不要继续动**；
- 当前要做的是：
  1. 把这轮问题和修复写清楚；
  2. 把问答部分重新对齐到“答案可跳转到论文原文页”。

因此，本文档后续不再把 PPT 扩面开发作为第一优先级，而是把它视作**阶段性已实现、可继续回归验证**的部分。

---

## 三、这轮真实遇到的主要问题、根因与修复

## 3.1 问题一：PPT 主链路入口不够收敛，导致定位困难

### 现象

用户一开始明确要求只用 `/ppt-master`，但系统里仍残留旧链路语义，导致出现这些排障困难：

- 不容易确认当前是否真的触发了 `/ppt-master`；
- 日志里看到的是“处理中”，但无法判断是旧逻辑、兼容逻辑还是新逻辑在跑；
- 一旦出错，很难界定问题是在主链路入口、Claude 批处理 prompt、还是产物发现阶段。

### 根因

根因不是某个函数单独写错，而是 **PPT 主流程的“单一事实来源”不够明确**。旧有思路、兼容路径和当前真实执行路径混在一起，导致排障时判断成本非常高。

### 已完成修复

这轮已经把后端默认 PPT 执行思路收敛到 `/ppt-master` 主链路，并围绕它增强了 batch prompt、产物发现和会话路径回写。结果是：

- 现在可以更明确地把问题归因到 `/ppt-master` 实际执行结果；
- PPT 主链路已经阶段性跑通；
- 后续 PPT 问题可以更多作为回归验证问题处理，而不再是“入口到底是谁”的架构问题。

### 当前结论

这一步的价值在于：**先把链路收窄，才能让后续所有错误变得可解释。**

---

## 3.2 问题二：产物定位策略不一致，导致“明明做了很多，系统却报失败”

### 现象

一个典型报错是：

- `Claude CLI completed but no project with svg_final/ found.`

用户感知上会自然理解为：

- 技能可能根本没触发；
- 项目没创建；
- 或者系统彻底失败。

但实际日志显示，很多时候 Claude 已经执行了相当一部分工作，甚至已经有部分项目目录和中间产物，只是**后端的 artifact discovery 认定条件过于僵硬**。

### 根因

核心根因是：

1. **项目存在** 与 **最终产物完整存在** 被混成了一个判断；
2. 系统把“没找到 `svg_final`”直接解释成“没找到项目”；
3. 项目目录、`notes/`、`svg_output/`、`svg_final/`、`pptx` 之间没有被清晰区分为不同完成度状态。

### 已完成修复

这轮已经对 `artifact_discovery` 语义和检测逻辑做了增强，重点包括：

- 更早识别 `project_dir`；
- 将“找到项目但产物不完整”和“完全没找到项目”区分开；
- 更准确地回写 `project_dir / slides_dir / notes_dir / ppt_path`；
- 避免把部分成功误报为完全失败。

修复后，错误语义从：

- “没有找到项目”

改成更接近真实情况的：

- “找到了项目，但只有 partial artifacts，缺少 `svg_final` 或 `PPTX` 导出”。

### 当前结论

这类问题说明：**产物发现不是简单的文件存在判断，而是运行状态建模问题。** 只要状态语义不清晰，系统就会出现大量“假失败”。

---

## 3.3 问题三：原始 PDF 的移动策略与 RAG / 会话输入职责冲突

### 现象

`/ppt-master` 工作流强调把源文件归档进项目目录的 `sources/`，这对技能自身来说是合理的；但对当前产品系统来说，如果直接把后端会话上传目录里的原始 PDF 移走，就会带来两个问题：

- RAG 侧仍然需要使用原始 PDF 建索引或提供原文；
- 会话级 `/api/sessions/{session_id}/pdf` 也需要稳定指向当前 session 的原始文档。

### 根因

根因是两个系统边界混淆：

- **技能内部的项目归档需求**
- **产品后端的长期可访问输入文件需求**

如果直接把 session 输入目录当成技能项目输入目录来“move”，就会破坏后端系统自己的数据约束。

### 已完成修复

这轮已经围绕此问题做了收口：

- 后端会话原始 PDF 不再被当作可以随意搬走的临时文件；
- `uploads/sessions/.../input/` 继续承担会话原始输入职责；
- PPT 正式产物与 RAG 缓存职责进一步分离；
- PPT 成品更多通过 repo 级 `projects/` 及其派生路径来定位，而不是反过来侵占 session 原始输入。

### 当前结论

这一步解决的是典型的**输入不可变性**问题：

> 原始上传文件应该被视为会话事实，不应被下游工作流随意搬迁并拿来兼任多个角色。

---

## 3.4 问题四：前端进度显示过粗，导致用户误以为系统卡死或没触发 skill

### 现象

用户多次反馈：

- PPT 一直显示生成中；
- RAG 一直在构建中；
- 百分比长期停在 10% / 12%；
- 看起来像没有触发 skill，或者后端已经挂住但没报错。

### 根因

根因不是“后端绝对没在干活”，而是：

1. **前端只看到了极粗粒度进度值**；
2. 百分比变化和真实产物生成节奏并不一致；
3. 用户看不到关键中间事实：
   - 是否已创建项目目录；
   - 是否已有 notes；
   - 是否已有初版 SVG；
   - 是否已有最终 SVG；
   - 是否已有 PPTX；
   - 最近 Claude / RAG 在输出什么日志。

### 已完成修复

这轮已经重点优化 `frontend/src/pages/ProgressPage.tsx`，新增或强化了：

- PPT / RAG 双任务分开展示；
- 更细的人类可读阶段提示；
- `project_dir` 展示；
- 讲稿 / 最终 SVG / PPTX 产物状态展示；
- 最近 PPT / RAG 日志；
- 当前提醒；
- WebSocket 不可用时回退到轮询并显示提示。

### 当前结论

这个问题的关键不是“把进度条做得更花”，而是：

> **用户必须能看到真实状态证据，而不是只看一个抽象百分比。**

---

## 3.5 问题五：错误语义不准，上游真实失败被次生错误遮蔽

### 现象

在多次真实测试中，日志最后显示的是统一失败，但用户难以判断：

- 是 Claude 本体失败；
- 是脚本执行失败；
- 是 artifact discovery 失败；
- 还是用户手动中断导致的结束。

尤其在 `artifact_discovery` 报错阶段，表层错误容易掩盖更早的真实根因。

### 根因

根因是系统当时更偏向“最终结果导向报错”，而不是“按阶段保留清晰因果链”。

也就是说，后面的失败节点把前面的失败语义覆盖掉了，导致用户只能看到最后一层表象。

### 已完成修复

这轮做的关键增强包括：

- 增强阶段化日志与错误信息透出；
- 在前端显示阶段名与 stdout/stderr tail；
- 把更接近真实失败点的上下文保留下来；
- 避免单一“处理失败”提示吞掉全部上下文。

### 当前结论

这类问题说明：**错误处理不是收尾工作，而是系统可用性的核心组成部分。**

---

## 3.6 问题六：Windows 环境下默认使用 `python3`，直接导致技能脚本执行失败

### 现象

在真实日志中，Claude 尝试执行类似命令：

- `python3 "...ppt-master/scripts/pdf_to_md.py" "...pdf"`

随后任务失败，tool result 出现：

- `Exit code 49`

### 根因

根因非常明确：

- 技能执行提示默认沿用了类 Unix 环境习惯；
- 但当前后端运行环境是 Windows；
- 在该环境中不能假定 `python3` 命令一定可用。

这不是 PPT 业务逻辑本身的问题，而是**运行环境约束没有在 prompt / 调用约定中前置表达清楚**。

### 已完成修复

这轮已经在 `backend/app/services/ppt_generator.py` 的 batch prompt 中加入明确约束：

- 当前是 Windows 后端任务；
- 不要假设 `python3` 存在；
- 如需运行 Python 脚本，优先使用当前解释器 `sys.executable`；
- 技能内脚本应使用绝对路径调用。

这一步是 PPT 最终能真正跑通的关键修复之一。

### 当前结论

这说明一个非常实际的教训：

> prompt 不是只负责“告诉模型做什么”，还必须告诉模型“当前环境能做什么、不能假设什么”。

---

## 3.7 问题七：系统可观测性不足，导致“看起来都像一个问题”

### 现象

用户在排障过程中多次需要手动查看 `generation.jsonl`，否则前端给出的信息远远不足以判断：

- 当前是否还在继续生成；
- 是 PPT 卡住还是 RAG 卡住；
- 是前端没收到事件还是后端确实没有进展；
- 中断是否来自用户手动停止还是任务自身报错。

### 根因

根因是**系统内部已经有一些状态，但没有被组织成用户能消费的观测面板**。

日志、阶段、产物、错误详情原本更像散落在不同层次的技术细节，而不是统一的会话视图。

### 已完成修复

这轮已经完成的改善包括：

- session snapshot 能带出 progress / stages / recent_logs / paths；
- 前端进度页能展示更完整的会话状态；
- 错误详情中可带出阶段、stdout_tail、stderr_tail；
- 日志接口失败时也会有显式的连接提示，而不是静默。

### 当前结论

这类问题背后的核心不是“缺少更多日志”，而是：

> **需要把运行状态重新组织为用户可理解的产品信息结构。**

---

## 四、这轮已经完成的关键修复总结

截至目前，可以把已经落地并产生明显效果的修复概括为：

### 4.1 PPT 主链路收口

- 后端主执行思路已收敛到 `/ppt-master`
- 历史混杂路径对排障的干扰明显降低

### 4.2 产物发现与路径回写增强

- 更早识别 `project_dir`
- 更清晰地区分 partial artifacts 与 final artifacts
- 更准确回写 `project_dir / slides_dir / notes_dir / ppt_path`

### 4.3 原始 PDF 保留策略对齐

- 会话输入目录中的原始 PDF 不再被轻易搬走
- RAG 与原文查看链路保持稳定输入来源

### 4.4 前端进度展示增强

- 不再只显示粗粒度百分比
- 能看到阶段、日志和产物状态
- 用户可以更快判断是“慢”还是“异常”

### 4.5 错误可见性增强

- 阶段信息更明确
- stdout/stderr tail 可见
- `artifact_discovery` 的错误语义更接近真实情况

### 4.6 Windows 执行约束修复

- 明确避免默认 `python3`
- 优先使用当前 Python 解释器与绝对路径
- 这是 PPT 真正跑通的重要前提

---

## 五、当前系统状态（2026-04-24）

### 5.1 PPT 部分的状态

当前应将 PPT 部分视为：

- **已经阶段性实现**；
- **已经完成本轮最重要的 P0 收口**；
- **可以继续做回归验证和小修补，但不应再作为当前主开发方向继续扩面。**

换句话说，PPT 现在最需要的是：

- 回归测试；
- 稳定性验证；
- 发现个别尾部问题时再最小修复。

而不是再重新拉起一轮“大统一架构重写”。

### 5.2 RAG / 问答部分的状态

问答部分并不是“完全没有原文跳转能力”，而是：

- 后端 `chat.py` 已经强制答案输出 `(第N页)`；
- 后端 `_parse_citations()` 已经会从答案中反解析实际引用页；
- 前端 `ChatPanel.tsx` 原本就能把 `(第N页)` 渲染为可点击按钮；
- `PdfViewer.tsx` 也仍可打开 `/api/sessions/{session_id}/pdf` 并跳到对应页。

所以当前问题更准确地说是：

- **能力基础还在**；
- **但来源展示不够显式、用户感知不够强、体验上像是“功能消失了”。**

---

## 六、为什么下一步要转向“答案可回指原文”

PPT 主链路本轮已经收口，而问答链路现在是更值得优先打磨的方向，原因有三点：

### 6.1 这是用户感知最强的价值点之一

对文献问答来说，最核心的信任来源不是“回答看起来像真的”，而是：

- 回答能指向论文原文；
- 用户能立刻点开查看对应页；
- 答案和来源之间关系清晰可见。

### 6.2 当前系统已经具备页级原文跳转基础

这不是从零开始开发，而是：

- 后端已有 `answer + sources` 返回结构；
- 前端已有行内 citation → PDF viewer 的链路；
- `/api/sessions/{session_id}/pdf` 已能提供原始 PDF。

因此现在更适合做的是 **体验补全**，而不是重写协议。

### 6.3 这是当前范围下投入产出比最高的改动

相比继续扩大 PPT 代码改动，问答原文定位增强：

- 影响面更小；
- 用户价值更直接；
- 更容易验证“是否真的变好了”。

---

## 七、下一步计划（明确收口版）

## 7.1 第一优先级：增强问答来源展示与原文跳转

目标：把当前“已有但不够显眼”的页级引用能力，变成用户一眼能感知、能点击、能回看的交互。

### 计划内容

1. **保留现有行内 citation 机制**
   - 继续使用答案中的 `(第N页)`
   - 继续把它渲染成可点击入口

2. **在 assistant 消息下方增加显式来源区**
   - 展示论文名 / 页码 / 原文片段摘要
   - 每条有页码的来源项都提供“查看原文”按钮

3. **统一复用现有 PDF viewer**
   - 所有来源跳转仍使用 `/api/sessions/{session_id}/pdf`
   - 当前只承诺页级跳转，不承诺页内高亮

4. **保持 schema 最小变更**
   - 优先继续复用当前 `answer + sources` 结构
   - 不为了 UI 小增强而重写整个聊天协议

## 7.2 第二优先级：把这轮经验固定成团队可复用知识

- 本文档即作为本轮问题复盘基线；
- 后续如果再出现 PPT 路径、进度或 artifact 误判问题，应优先回到这里核对：
  - 是旧问题回归；
  - 还是新增问题。

## 7.3 当前明确不做的事

以下事项当前**不在本轮范围内**：

- 不继续大改 `/ppt-master` 主链路；
- 不继续扩展 PPT 新能力；
- 不重做 RAG 索引或切换向量库；
- 不实现 PDF 页内坐标级高亮；
- 不重写整套聊天状态管理与后端响应 schema。

---

## 八、对这轮工作的最终判断

如果把这轮工作简单理解成“修了几个 bug”，是不准确的。

更准确的结论是：

1. **PPT 主链路已经完成了一次必要的 P0 收口**；
2. **真正导致反复排障的，不是单点逻辑错误，而是链路耦合、产物发现不一致、平台假设错误和可观测性不足的叠加**；
3. **当前最合理的下一步不是继续扩大 PPT，而是把问答链路升级到“答案可直接回指原文页”的可验证体验。**

这也意味着，当前系统的阶段目标已经发生变化：

- 前一阶段：**先把 PPT 做通**；
- 当前阶段：**把问答做得可信、可追溯、可跳回原文。**
---

## 8. 2026-04-24 Q&A / RAG Optimization Addendum

### 8.1 What changed

- RAG cache version was bumped from `v3` to `v4`.
  This forces fresh index builds so the new retrieval logic actually takes effect instead of silently reusing older cached indexes.

- Retrieval moved from pure vector search to hybrid retrieval.
  The current path is:
  1. vector retrieval for semantic recall
  2. lightweight BM25-style lexical retrieval over persisted `docstore.json`
  3. RRF-based fusion and reranking
  4. final source dedupe, context-length control, and source-count limiting

- The embedding model is now expected to live in the project directory:
  - `backend/models/bge-m3`
  - `backend/models/cache`

### 8.2 Why this was necessary

- Pure vector retrieval was good for broad semantic matching, but still weak on exact technical terms such as model names, dataset names, table numbers, and section-specific keywords.
- Older cached indexes could still contain noisy back matter or reference-like text, which made citations look like bibliography entries instead of main-body evidence.
- Without a cache-version upgrade, code changes alone would not change user-visible retrieval quality.

### 8.3 Current Q&A flow

1. After PDF upload, the system launches PPT generation and RAG indexing in parallel.
2. The RAG task checks the session-independent cache using the PDF hash plus cache version `v4`.
3. On cache miss, `rag_index.py` parses the PDF, trims reference sections, filters noisy paragraphs, chunks the main body, and builds the vector index.
4. At question time, the system runs hybrid retrieval on the session index and assigns source ids such as `C1`, `C2`, `C3`.
5. The LLM answers with inline citation markers like `[[C1]]` at the sentence level.
6. The frontend renders those markers as clickable references and opens the PDF at the cited page on demand, while keeping source details collapsed by default.

### 8.4 Direct benefits

- New sessions and rebuilt indexes no longer reuse stale `v3` retrieval results.
- Questions containing exact paper terms should retrieve more precisely.
- Semantic recall is preserved because vector retrieval remains the first-stage backbone.
- The answer-first UI stays cleaner because evidence remains collapsed until the user wants to inspect it.

### 8.5 Recommended next steps

- Add a reranker on top of the current hybrid retrieval stack.
- Add query rewriting for broad questions such as "What does this paper say?".
- Introduce conversation memory only for query rewriting and context carry-over, not as a substitute for evidence retrieval.
- Extend indexing beyond plain paragraphs to include section headers, figure captions, tables, and formula-adjacent content.
- Add an explicit cache cleanup policy for historical RAG index versions.
