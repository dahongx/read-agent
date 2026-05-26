# ZEP时序知识图谱论文汇报 - Design Spec

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | zep_temporal_kg_memory_ppt169_20260525 |
| **Canvas Format** | PPT 16:9 (1280×720) |
| **Page Count** | 12页 |
| **Design Style** | 学术汇报（Academic Consulting） |
| **Target Audience** | 高校师生 |
| **Use Case** | 论文汇报、学术报告 |
| **Created Date** | 2026-05-25 |

---

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280×720 px |
| **viewBox** | `0 0 1280 720` |
| **Margins** | 左右 40px，上 0px，下 35px |
| **Content Area** | x: 40–1240，y: 70–665 |

---

## III. Visual Theme

### Theme Style

- **Style**: 学术汇报
- **Theme**: 浅色主题（白色背景 + 深蓝标题栏）
- **Tone**: 严谨、专业、数据驱动、层次清晰

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#FFFFFF` | 页面主背景 |
| **Secondary bg** | `#E8F4FC` | 卡片背景、信息块 |
| **Primary** | `#003366` | 标题栏、章节标题、主标题 |
| **Accent Blue** | `#0066CC` | 卡片边框、图标、次要装饰 |
| **Accent Orange** | `#F07C00` | 关键数据高亮、橙色强调（替代模板红色） |
| **Card Gray** | `#F5F7FA` | 卡片内部背景、信息块 |
| **Body text** | `#333333` | 正文内容 |
| **Secondary text** | `#666666` | 说明、注释 |
| **Tertiary text** | `#999999` | 页脚、辅助信息 |
| **Border/divider** | `#D0D7E0` | 卡片边框、分隔线 |
| **Success** | `#28A745` | 正向指标（绿色） |
| **Warning** | `#F07C00` | 橙色强调（与 Accent Orange 统一） |

> 配色说明：基于 academic_defense 模板，将原红色 #CC0000 替换为橙色 #F07C00 以符合用户"蓝白为主，橙色强调"需求。

### Gradient Scheme

```xml
<!-- 章节页深蓝背景 -->
<linearGradient id="chapterBg" x1="0%" y1="0%" x2="100%" y2="100%">
  <stop offset="0%" stop-color="#003366"/>
  <stop offset="100%" stop-color="#0066CC" stop-opacity="0.85"/>
</linearGradient>
```

---

## IV. Typography System

### Font Plan

**Recommended preset**: P1（现代商务/科技）

| Role | Chinese | English | Fallback |
| ---- | ------- | ------- | -------- |
| **Title** | Microsoft YaHei / 微软雅黑 | Arial | sans-serif |
| **Body** | Microsoft YaHei / 微软雅黑 | Calibri | sans-serif |
| **Code** | - | Consolas | Monaco |
| **Emphasis** | SimHei / 黑体 | Arial Black | sans-serif |

**Font stack**: `"Microsoft YaHei", "微软雅黑", Arial, sans-serif`

### Font Size Hierarchy

**Baseline**: Body font size = 16px（内容密度偏高，选 dense 基线；用户要求14-16pt）

| Purpose | Ratio | Size | Weight |
| ------- | ----- | ---- | ------ |
| Cover main title | 3x | 48px | Bold |
| Page title (H2) | 1.75x | 28px | Bold |
| Section title (H3) | 1.5x | 24px | Bold |
| Card title (H4) | 1.25x | 20px | Bold |
| **Body content** | **1x** | **16px** | Regular |
| Annotation | 0.875x | 14px | Regular |
| Footer/page number | 0.75x | 12px | Regular |
| Key data highlight | 2.25x | 36px | Bold |

---

## V. Layout Principles

### Page Structure（遵循 academic_defense 模板）

- **Header area**: y=0, h=70px — 深蓝背景 + 橙色左竖条 + 页面标题
- **Key Message Bar**: y=70, h=50px — 核心消息区（浅蓝灰背景）
- **Content area**: y=135, h=515px — 主内容区（灵活布局）
- **Footer area**: y=665, h=55px — 数据来源、章节名、页码

### Common Layout Modes

| Mode | Suitable Scenarios |
| ---- | ----------------- |
| **单列居中** | 封面、结束页、关键观点 |
| **左右分栏（5:5）** | 对比分析、双概念 |
| **左右分栏（4:6）** | 图文混排 |
| **三列卡片** | 特性列表、三层结构 |
| **两列卡片** | 目录、对比项 |
| **表格布局** | 实验数据对比 |
| **流程图横向** | 检索管道、处理流程 |

### Spacing Specification

| Element | Value |
| ------- | ----- |
| Card gap | 20px |
| Content block gap | 24px |
| Card padding | 20px |
| Card border radius | 8px |
| Icon-text gap | 12px |

---

## VI. Icon Usage Specification

### Source

- **Icon library**: `tabler-outline`（线条风格，适合学术汇报屏幕展示）
- **Usage format**: `{{icon:tabler-outline/icon-name}}`

### Icon Inventory

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| 记忆/大脑 | `tabler-outline/brain` | P03 背景/动机 |
| 数据库/存储 | `tabler-outline/database` | P04 图谱构建 |
| 时间/时序 | `tabler-outline/clock` | P05 双时态模型 |
| 网络/连接 | `tabler-outline/cloud-network` | P06 社区子图 |
| 搜索/检索 | `tabler-outline/adjustments-search` | P07 记忆检索 |
| AI/智能体 | `tabler-outline/ai-agent` | P03 背景 |
| 速度/延迟 | `tabler-outline/bolt` | P10 结果 |
| 柱状图/性能 | `tabler-outline/chart-bar` | P09 DMR结果 |

---

## VII. Chart Reference List

| Chart Type | Reference Template | Used In | Purpose |
| ---------- | ------------------ | ------- | ------- |
| `horizontal_bar_chart` | `templates/charts/horizontal_bar_chart.svg` | Slide 09 | DMR各方法准确率对比 |
| `grouped_bar_chart` | `templates/charts/grouped_bar_chart.svg` | Slide 10 | LongMemEval准确率与延迟对比 |
| `kpi_cards` | `templates/charts/kpi_cards.svg` | Slide 11 | 核心贡献数字摘要 |

---

## VIII. Image Resource List

无AI生成图片，使用文字+图表+数据可视化（SVG手绘图）。

---

## IX. Content Outline

### Part 1: 开场

#### Slide 01 - 封面（01_cover.svg 类型）

- **Layout**: 封面居中布局（deep blue top bar + orange left bar decoration）
- **Title**: ZEP：面向智能体记忆的时序知识图谱架构
- **Subtitle**: ZEP: A Temporal Knowledge Graph Architecture for Agent Memory
- **Info**: Zep AI团队 · arXiv:2501.13956 · 2025年1月
- **Bottom**: 汇报人：[学生姓名] | 指导教师：[教师姓名]

---

### Part 2: 结构概览

#### Slide 02 - 目录（02_toc.svg 类型）

- **Layout**: 两列卡片式目录（6项）
- **Title**: 目录
- **TOC Items**:
  1. 研究背景与动机
  2. 知识图谱构建
  3. 双时态模型与实体关系
  4. 记忆检索系统
  5. 实验结果
  6. 结论与贡献

---

### Part 3: 研究背景

#### Slide 03 - 研究背景与动机（03_content.svg 类型）

- **Layout**: 左右分栏（4:6）—— 左侧问题三点，右侧解决方案框架
- **Title**: 为什么需要智能体记忆？
- **Key Message**: LLM 上下文窗口有限，传统 RAG 无法处理动态演化的企业数据
- **Content**:
  - **问题三点（左侧卡片）**:
    - 上下文窗口限制：无法存储完整对话历史（企业场景平均 115k tokens）
    - 静态 RAG 局限：现有框架只能检索静态文档语料，无法追踪关系演化
    - 幻觉风险：缺乏结构化记忆导致 LLM 生成错误信息
  - **解决思路（右侧）**:
    - Zep = 时序知识图谱引擎 Graphiti
    - 动态摄入非结构化对话 + 结构化业务数据
    - 维护事实时效性与历史关系轨迹
- **Icon**: `tabler-outline/ai-agent`（左侧装饰）、`tabler-outline/brain`

---

#### Slide 04 - 知识图谱三层架构（03_content.svg 类型）

- **Layout**: 三列卡片（三个子图层）+ 底部整体说明
- **Title**: Zep 知识图谱：三层分级结构
- **Key Message**: 从原始对话到高层社区摘要，三层子图实现从细节到全局的记忆组织
- **Content**:
  - **第一层 — 情节子图 Ge**:
    - 存储原始输入（消息/文本/JSON）
    - 无损数据层，支持溯源引用
    - 包含参考时间戳 t_ref
  - **第二层 — 语义实体子图 Gs**:
    - 从情节中提取命名实体与事实关系
    - 实体向量化（1024维）+ 混合搜索去重
    - 对应人类语义记忆（Semantic Memory）
  - **第三层 — 社区子图 Gc**:
    - 基于标签传播聚类形成社区节点
    - 高层摘要，支持全局域理解（受 GraphRAG 启发）
    - 动态扩展，延迟完整刷新
- **Bottom note**: 类比心理学：情节记忆（events）→ 语义记忆（associations）→ 概念社区
- **Icon**: `tabler-outline/database`

---

### Part 4: 核心技术

#### Slide 05 - 双时态模型与实体事实提取（03_content.svg 类型）

- **Layout**: 上下两区——上方双时态说明（横向流程图），下方三步提取流程
- **Title**: 双时态建模：精确追踪事实有效期
- **Key Message**: 时间轴 T（事件顺序）+ 事务轴 T'（数据摄入顺序），四个时间戳管理事实生命周期
- **Content**:
  - **双时态模型（上区，横向流程）**:
    - T 轴（现实世界时间）：t_valid → t_invalid（事实何时成立）
    - T' 轴（系统摄入时间）：t'_created → t'_expired（系统何时录入）
    - 新事实可自动失效矛盾旧边（LLM 判断语义冲突）
  - **实体与事实提取流程（下区，三步）**:
    - Step 1 实体提取：NER + Reflexion反思减幻觉，向量嵌入+全文搜索解析重复实体
    - Step 2 事实提取：抽取主语-谓语-宾语三元组，支持超边建模（同一事实涉及多实体）
    - Step 3 图集成：Cypher预定义查询写入 Neo4j（避免LLM生成查询的不一致风险）
- **Icon**: `tabler-outline/clock`

---

#### Slide 06 - 社区子图与动态图构建（03_content.svg 类型）

- **Layout**: 左右分栏（5:5）—— 左侧社区检测机制，右侧图构建完整流程
- **Title**: 社区子图与增量图构建
- **Key Message**: 标签传播动态扩展，支持流数据持续摄入，同时控制 LLM 调用成本
- **Content**:
  - **左侧 — 社区检测（vs GraphRAG）**:
    - GraphRAG 使用 Leiden 算法（全批量）
    - Zep 使用标签传播（动态单步扩展）
    - 新节点加入时只更新邻居社区，延迟全量刷新
    - 社区名含关键词嵌入，支持余弦相似度检索
  - **右侧 — 完整图构建流程（纵向步骤）**:
    - 摄入 Episode（消息/文本/JSON）
    - 实体提取 + 向量化 + 实体解析（去重）
    - 事实提取 + 时间抽取 + 边失效检测
    - 社区检测（标签传播动态扩展）
    - 写入 Neo4j 知识图谱
- **Icon**: `tabler-outline/cloud-network`

---

#### Slide 07 - 记忆检索三阶段管道（03_content.svg 类型）

- **Layout**: 横向三步流程图（Search → Reranker → Constructor）+ 下方三种搜索方式卡片
- **Title**: 记忆检索：三阶段管道
- **Key Message**: f(α) = χ(ρ(φ(α))) — 搜索召回、重排精排、上下文构造三步组合
- **Content**:
  - **顶部横向流程**:
    - φ(Search)：并行执行三种搜索，生成候选三元组（语义边、实体节点、社区节点）
    - ρ(Reranker)：RRF / MMR / Episode频率重排 / 节点距离重排 / 交叉编码器精排
    - χ(Constructor)：格式化为 FACTS + ENTITIES 上下文字符串输出给 LLM
  - **下方三种搜索卡片**:
    - 余弦语义搜索 φ_cos：捕捉语义相似性（向量空间）
    - BM25全文搜索 φ_bm25：捕捉词汇相似性（TF-IDF类）
    - 广度优先搜索 φ_bfs：捕捉上下文相似性（n跳图邻域）
- **Icon**: `tabler-outline/adjustments-search`

---

### Part 5: 实验结果

#### Slide 08 - 实验设置（03_content.svg 类型）

- **Layout**: 左右分栏（5:5）—— 左侧两个基准介绍，右侧模型配置表格
- **Title**: 实验设计与基准选择
- **Key Message**: 两大基准覆盖不同难度：DMR测单会话简单检索，LongMemEval测长对话复杂时序推理
- **Content**:
  - **左侧 — 两大基准**:
    - **DMR（Deep Memory Retrieval）**：500条多会话对话，每条5个会话×12条消息，单轮事实问答
    - **LongMemEval (LME-s)**：企业场景长对话，平均115k tokens，6种问题类型（跨会话、时序推理等）
  - **右侧 — 模型配置**:
    - 嵌入/重排：BGE-m3（BAAI）
    - 图构建：gpt-4o-mini-2024-07-18
    - 回答生成：gpt-4o-mini / gpt-4o-2024-11-20
    - 历史对比（DMR）：gpt-4-turbo-2024-04-09
    - 测试环境：消费级笔记本，远程连接 AWS us-west-2 Zep 服务

---

#### Slide 09 - DMR基准测试结果（03_content.svg 类型）

- **Layout**: 居中横向条形图 + 右侧结论卡片
- **Title**: DMR 基准结果：Zep 超越 MemGPT
- **Key Message**: Zep（94.8%）超过 MemGPT（93.4%），但 DMR 本身局限性限制了区分度
- **Chart**: `horizontal_bar_chart`（横向柱状图）
- **Data**:
  - Recursive Summarization (gpt-4-turbo): 35.3%
  - Conversation Summaries (gpt-4-turbo): 78.6%
  - **MemGPT (gpt-4-turbo): 93.4%** ← 当前 SOTA
  - Full-context (gpt-4-turbo): 94.4%
  - **Zep (gpt-4-turbo): 94.8%** ← 橙色高亮
  - Full-context (gpt-4o-mini): 98.0%
  - **Zep (gpt-4o-mini): 98.2%** ← 橙色高亮
- **右侧结论卡片**:
  - DMR局限：对话仅60条消息，可完整放入上下文窗口
  - 评估缺陷：单轮事实问答，不考察复杂时序推理
  - 更有价值的评测 → LongMemEval

---

#### Slide 10 - LongMemEval结果（03_content.svg 类型）

- **Layout**: 双组柱状图（准确率）+ KPI数字卡片（延迟对比）
- **Title**: LongMemEval：显著提升准确率，大幅降低延迟
- **Key Message**: Zep 准确率提升 15.2–18.5%，响应延迟降低 90%，上下文 tokens 压缩 99%
- **Chart**: `grouped_bar_chart`（准确率对比）
- **Data（准确率）**:
  - Full-context gpt-4o-mini: 55.4% → Zep gpt-4o-mini: 63.8% (+15.2%)
  - Full-context gpt-4o: ~62% → Zep gpt-4o: ~73% (+18.5%)
- **KPI卡片（延迟/规模）**:
  - 延迟: Full-context 31.3s → Zep 3.20s（**降低 90%**）
  - 上下文: 115k tokens → 1.6k tokens（**压缩 99%**）
  - IQR（延迟稳定性）: 8.76s → 1.6s（**更稳定**）
- **Icon**: `tabler-outline/bolt`

---

### Part 6: 总结

#### Slide 11 - 主要贡献与结论（03_content.svg 类型）

- **Layout**: 上方三列贡献卡片 + 下方一行核心数字 KPI
- **Title**: 核心贡献总结
- **Key Message**: Zep 通过时序知识图谱实现了精度、延迟、可扩展性三维兼顾的企业级记忆方案
- **Content**:
  - **三大技术贡献**:
    - Graphiti 时序 KG 引擎：双时态建模 + 非无损情节存储，准确追踪事实演化
    - 三层分级架构：情节→语义→社区，类比人类记忆，支持细粒度到全局检索
    - 混合检索 + 重排管道：余弦+BM25+BFS三路召回，多策略精排
  - **KPI数字行（橙色高亮）**:
    - +18.5% 准确率提升（LongMemEval）
    - -90% 响应延迟（3.2s vs 31.3s）
    - -99% 上下文 tokens（1.6k vs 115k）
    - 94.8% DMR 精度（超越 MemGPT）

---

#### Slide 12 - 结束页（04_ending.svg 类型）

- **Layout**: 居中结束页（深蓝顶栏）
- **Thank You**: 感谢聆听！欢迎提问
- **Tagline**: Zep: Empowering AI Agents with Temporal Memory
- **Contact**: arXiv:2501.13956v1 | getzep.com
- **Bottom**: Q & A

---

## X. Speaker Notes Requirements

- **File naming**: 与 SVG 文件名对应，如 `01_cover.md`、`02_toc.md` ...
- **Style**: 口语化中文，每页 100–200 字，讲解论文内容，不讲排版
- **Purpose**: 论文内容讲解（inform）
- **Duration**: 全程约 20 分钟（每页平均约 1.5 分钟）

---

## XI. Technical Constraints Reminder

### SVG Generation Must Follow:

1. viewBox: `0 0 1280 720`
2. Background uses `<rect>` elements
3. Text wrapping uses `<tspan>` (`<foreignObject>` FORBIDDEN)
4. Transparency uses `fill-opacity` / `stroke-opacity`; `rgba()` FORBIDDEN
5. FORBIDDEN: `clipPath`, `mask`, `<style>`, `class`, `foreignObject`
6. FORBIDDEN: `textPath`, `animate*`, `script`, `marker`/`marker-end`
7. Arrows use `<polygon>` triangles instead of `<marker>`
8. 橙色强调使用 #F07C00，替代模板原 #CC0000

### PPT Compatibility Rules:

- `<g opacity="...">` FORBIDDEN; set opacity on each child element individually
- Inline styles only; external CSS and `@font-face` FORBIDDEN

---

## XII. Design Checklist

### Pre-generation
- [x] 内容量适合页面容量（平均4-6个要点/页）
- [x] 布局模式与内容类型匹配
- [x] 配色语义使用正确（橙色=强调/数据，蓝色=结构/标题）

### Post-generation
- [ ] viewBox = `0 0 1280 720`
- [ ] 无 `<foreignObject>` 元素
- [ ] 所有文字可读（≥12px）
- [ ] 内容在安全区内
- [ ] 元素对齐
- [ ] 同类元素风格一致
- [ ] 配色符合规范

---

## XIII. Next Steps

1. ✅ 设计规范生成完毕
2. 无 AI 生成图片 → 直接进入 **Executor** 角色生成 SVG
