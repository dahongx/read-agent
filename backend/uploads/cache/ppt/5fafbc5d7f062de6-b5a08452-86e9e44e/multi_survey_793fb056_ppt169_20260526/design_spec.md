# Design Specification & Content Outline
# 大型语言模型长期记忆与认知建模综述

---

## I. Project Information

| Field | Value |
|-------|-------|
| **Project Name** | multi_survey_793fb056 |
| **Canvas Format** | PPT 16:9 |
| **Page Count** | 12 pages |
| **Style** | General Consulting (学术汇报) |
| **Target Audience** | 高校师生 |
| **Occasion** | 论文综述汇报 |
| **Core Message** | 两篇新兴研究从"时序感知会话记忆"与"长程认知建模"两个视角推进了LLM长期记忆机制，各自在标准基准上取得最新最优结果，共同揭示了结构化记忆与推理耦合的重要性 |
| **Date** | 2026-05-26 |
| **Language** | 中文 |

---

## II. Canvas Specification

| Property | Value |
|----------|-------|
| **Format** | Standard 16:9 |
| **Dimensions** | 1280 × 720 px |
| **viewBox** | `0 0 1280 720` |
| **Page Margins** | Left/Right 40px, Top 0px, Bottom 35px |
| **Safe Area** | x: 40–1240, y: 70–685 |
| **Header Area** | y=0, h=70px |
| **Key Message Bar** | y=70, h=50px |
| **Content Area** | y=135, h=510px |
| **Footer Area** | y=665, h=55px |

---

## III. Visual Theme

| Property | Value |
|----------|-------|
| **Theme Mode** | Light (white background + dark blue title bar) |
| **Tone** | Professional, rigorous, academic |
| **Overall Style** | Clean grid layout, structured academic defense |

### Color Scheme

| Role | HEX | Usage |
|------|-----|-------|
| **Primary Dark Blue** | `#003366` | Header background, section titles, main headings |
| **Accent Blue** | `#0066CC` | Card borders, icons, secondary decorations, links |
| **Accent Orange** | `#E87722` | Key highlights, keyword emphasis, left decorative bar (replaces template red) |
| **Light Blue-Gray** | `#E8F4FC` | Key message bar background, card inner sections |
| **Background White** | `#FFFFFF` | Page main background |
| **Primary Text** | `#333333` | Body content |
| **Secondary Text** | `#666666` | Descriptions, annotations |
| **Muted Gray** | `#999999` | Footer, auxiliary info |
| **Card Gray** | `#F5F7FA` | Card inner background |
| **Border Gray** | `#D0D7E0` | Card borders, dividers |

### Gradient Scheme

- Header gradient: `#003366` → `#004A99` (left to right, subtle)
- Highlight bar: `#E87722` solid, width 6px vertical bar

---

## IV. Typography System

### Font Stack

**Primary**: `"Microsoft YaHei", "微软雅黑", Arial, sans-serif`

### Font Size Hierarchy

| Level | Usage | Size | Weight |
|-------|-------|------|--------|
| H1 | Cover main title | 52px | Bold |
| H2 | Page title (in header) | 26px | Bold |
| H3 | Section/card title | 22px | Bold |
| H4 | Sub-item title | 18px | Bold |
| P | Body content | 17px | Regular |
| High | Highlighted data/numbers | 36px | Bold |
| Sub | Notes/sources/captions | 13px | Regular |
| XS | Footer / page number | 12px | Regular |

> Body baseline: 17px (dense academic content, 6+ items per page)

---

## V. Layout Principles

### Page Structure

| Zone | Y Position | Height | Description |
|------|-----------|--------|-------------|
| Header | y=0 | 70px | Dark blue bg + orange left bar (6px) + white page title |
| Key Message Bar | y=70 | 50px | Light blue-gray bg + blue left bar + summary sentence |
| Content Area | y=135 | 510px | Freely laid out per page design |
| Footer | y=665 | 55px | Data source, section name, page number |

### Layout Modes

| Mode | Suitable Pages |
|------|---------------|
| Single column centered | Cover, Chapter, Ending |
| Two-column cards (5:5) | TOC, Comparison, Limitations |
| Two-column (4:6) | Architecture pages with figure |
| Three-column equal | Method overview, Feature cards |
| Card grid (2×2) | Key results, Ablation summary |
| Table layout | Experiment data comparison |

### Spacing

| Element | Value |
|---------|-------|
| Card gap | 20px |
| Content block gap | 24px |
| Card padding | 20px |
| Card border radius | 8px |
| Icon-text gap | 10px |
| Section vertical gap | 30px |

---

## VI. Icon Usage Spec

**Library**: `tabler-outline` (线条图标，清雅学术风)
**Usage**: Moderate, mainly for section labels and feature points

### Approved Icon Inventory

| Icon Name | Usage Page |
|-----------|-----------|
| `tabler-outline/brain` | 研究背景 — 记忆/认知 |
| `tabler-outline/calendar` | 研究背景 — 时序记忆 |
| `tabler-outline/database` | 方法页 — 知识库/存储 |
| `tabler-outline/database-search` | 方法页 — 检索 |
| `tabler-outline/chart-bar` | 实验结果 — 数据图 |
| `tabler-outline/chart-line` | 消融分析 |
| `tabler-outline/ai-agent` | Chronos Agent / 智能体 |
| `tabler-outline/filter` | 检索过滤 |
| `tabler-outline/bulb` | 结论/创新点 |
| `tabler-outline/alert-triangle` | 局限性 |
| `tabler-outline/books` | 综述/文献 |
| `tabler-outline/cpu` | 模型/计算 |

> Executor may only use icons from the above list.

---

## VII. Chart Reference List

| Chart Type | Used On Page | Purpose |
|-----------|-------------|---------|
| Horizontal bar chart (custom) | 09_实验结果 | Chronos vs baselines accuracy comparison |
| Table with color coding | 09_实验结果 | Category-level accuracy across methods |
| Bar chart (custom) | 10_消融分析 | Ablation contribution per component |
| Comparison table | 07_认知建模框架 | WebShop comparative results |

---

## VIII. Image Resource List

| Filename | Source | Layout Suggestion | Purpose | Status |
|---------|--------|------------------|---------|--------|
| `chronos_architecture.png` | Paper 1 Fig 1 | Right panel, 4:6 left-text right-image | Chronos系统架构图 | Existing |
| `chronos_benchmark.png` | Paper 1 Fig 2 | Bottom half, full-width | 基准测试准确率对比图 | Existing |
| `chronos_error_analysis.png` | Paper 1 Fig 3 | Right panel | 错误分类分析图 | Existing |
| `cognitive_framework.jpg` | Paper 2 Fig 1 | Right panel, 4:6 | 认知建模总体架构 | Existing |
| `cognitive_entropy.png` | Paper 2 Fig 2 | Right panel | 熵正则系数影响曲线 | Existing |
| `cognitive_memory_cap.png` | Paper 2 Fig 3 | Bottom area | 记忆容量敏感性实验 | Existing |

> All images are in `images/` directory. Reference with `../images/<filename>`.

---

## IX. Content Outline

### Page 01 — 封面（Cover）
**Template**: `templates/01_cover.svg`
**Layout**: Single column centered

- **主标题**: LLM 长期记忆机制综述
- **副标题**: 时序感知会话记忆 × 长程认知建模
- **汇报人**: （汇报者）
- **指导教师**: （指导老师）
- **机构**: （单位）
- **日期**: 2026年5月26日
- **橙色 tag**: 论文综述汇报

---

### Page 02 — 目录（TOC）
**Template**: `templates/02_toc.svg`
**Layout**: Two-column card grid

| 编号 | 章节 | 摘要 |
|------|------|------|
| 01 | 研究背景与动机 | 长期记忆的挑战与研究意义 |
| 02 | 核心问题定义 | 时序推理与长程决策的双重困境 |
| 03 | 方法脉络 | Chronos 与认知建模框架对比解析 |
| 04 | 实验结果 | LongMemEvalS 与 WebShop 评测数据 |
| 05 | 消融分析 | 各组件贡献度与设计权衡 |
| 06 | 局限性与展望 | 挑战、不足及未来研究方向 |

---

### Page 03 — 研究背景与动机
**Template**: `templates/03_content.svg`
**Layout**: Three-column cards + key message bar
**Key Message**: 现有 LLM 记忆系统在"时序推理"与"跨时段决策一致性"上存在系统性短板

**Cards**:
1. **会话记忆的规模挑战** [icon: tabler-outline/books]
   - 会话可跨越数周至数月
   - 现有上下文窗口无法涵盖全部历史
   - 密集提取 vs 简单召回的权衡难题
2. **时序信息的失真** [icon: tabler-outline/calendar]
   - 现有系统将时间表达式当作普通字符串
   - 无法进行"上个月做了什么"类精确过滤
   - 跨会话事件聚合准确率低
3. **长程决策的碎片化** [icon: tabler-outline/brain]
   - 智能体过度依赖短期状态
   - 历史经验未能显式参与当前决策推理
   - 长期目标一致性难以维持

**Footer**: Sources: Chronos (arXiv:2603.16862) | Cognitive Modeling (preprints202602.1990)

---

### Page 04 — 核心问题定义
**Template**: `templates/03_content.svg`
**Layout**: Two-column split (left: Paper 1 problem; right: Paper 2 problem)
**Key Message**: 两篇论文从互补角度定义问题：前者聚焦时序记忆精确召回，后者关注记忆驱动的长程策略

**Left Card — [Chronos]**:
- **研究问题**: 对话系统如何精确回答"时间敏感型"查询？
- 现有检索系统对 "relative date" / "event sequences" 无法进行结构化过滤
- 多跳时序查询（如"度假后那一周做了什么"）准确率极低
- 核心挑战：**无法将结构化时序信息与语义检索解耦**

**Right Card — [认知建模]**:
- **研究问题**: 长程顺序任务中，智能体如何系统利用历史经验？
- 现有策略模型局限于短期状态或隐式压缩历史
- 记忆储存与决策生成相互脱节
- 核心挑战：**缺乏感知-记忆-推理-决策的统一认知闭环**

**Footer**: 两个问题均指向同一本质：结构化长期记忆需要与推理机制深度耦合

---

### Page 05 — 章节页：方法脉络
**Template**: `templates/02_chapter.svg`
**Layout**: Chapter page

- **章节号**: 03
- **章节标题**: 方法脉络
- **章节描述**: Chronos 时序感知框架 × 认知建模学习框架

---

### Page 06 — Chronos 架构解析
**Template**: `templates/03_content.svg`
**Layout**: Left text (4 units) + Right image (6 units)
**Key Message**: Chronos 以"最小充分抽象"原则，仅结构化时序事件，保留原始对话语义

**Right**: embed `chronos_architecture.png`

**Left Content (4 components)**:
1. **事件提取管道** [icon: tabler-outline/database]
   - ⟨subject, verb, object⟩ 三元组 + ISO 8601 精确时间范围
   - 多分辨率时间归一化（精确/相对/模糊）
   - 生成 2–4 个词汇别名增强检索召回
2. **动态提示系统** [icon: tabler-outline/ai-agent]
   - 每个查询独立生成检索指导（动态 preamble）
   - 区分：时间过滤型 / 偏好召回型 / 跨会话聚合型
   - Gemini 3 Flash 单次推理生成
3. **初始检索阶段** [icon: tabler-outline/database-search]
   - 向量检索 Top-100 → Cohere Rerank v3 → Top-15
   - 前后各扩展 1 轮对话上下文
4. **Chronos Agent** [icon: tabler-outline/filter]
   - ReAct 推理循环：vector search + grep 双工具
   - 迭代式证据积累直至置信度满足

**Footer**: Paper 1: Chronos (Lumer et al., 2026) | Eval: LongMemEvalS (500 questions)

---

### Page 07 — 认知建模框架解析
**Template**: `templates/03_content.svg`
**Layout**: Left text + Right image (4:6)
**Key Message**: 统一认知闭环将感知表征、长期记忆、推理模块与策略生成耦合为端到端学习框架

**Right**: embed `cognitive_framework.jpg`

**Left Content**:
- **感知表征**: h_t = f_enc(o_t)，区分短期感知与长期认知存储
- **长期记忆管理**: 选择性写入机制 M_{t+1} = M_t ∪ g_write(h_t, M_t)；稳定性-可塑性平衡
- **记忆检索推理**: 注意力机制 α_t = softmax(h_t · m_i)；聚合表示 r_t 参与当前决策逻辑
- **策略生成**: z_t = φ(h_t, r_t)；行为由当前环境 + 长期认知结构共同驱动

**Comparison Table** (compact):

| 维度 | Chronos | 认知建模框架 |
|------|---------|------------|
| 记忆类型 | 事件历法 + 对话历法 | 抽象记忆向量集合 |
| 检索方式 | 向量 + grep 双模态 | 注意力机制 |
| 推理方式 | ReAct 工具调用循环 | 记忆驱动策略生成 |
| 场景 | 长期对话问答 | 长程顺序决策 |

**Footer**: Paper 2: Yang et al. (2026) | Eval: WebShop interactive dataset

---

### Page 08 — 章节页：核心实验结果
**Template**: `templates/02_chapter.svg`
**Layout**: Chapter page

- **章节号**: 04
- **章节标题**: 核心实验结果
- **章节描述**: LongMemEvalS 基准 × WebShop 交互评测

---

### Page 09 — 实验结果对比
**Template**: `templates/03_content.svg`
**Layout**: Two-column — left: Chronos results table; right: Cognitive results table
**Key Message**: 两个框架在各自领域均取得最优结果，结构化记忆是共同关键驱动因素

**Left: LongMemEvalS 结果**

| 方法 | 总准确率 | KU | MS | TR |
|------|---------|----|----|-----|
| **Chronos Low** | **92.60%** | 96.15% | 91.73% | 94.29% |
| Honcho | 90.00% | 94.87% | 84.96% | 88.72% |
| EmergenceMem | 86.00% | 83.33% | 81.20% | 85.71% |
| Mastra | 84.80% | 85.90% | 79.70% | 85.71% |
| Zep | 71.20% | 83.30% | 57.90% | 62.40% |

- Chronos High (Opus 4.6): **95.60%** (+3.02% over prior SOTA)

**Right: WebShop 结果**

| 方法 | SR% | Avg.Steps | SPL% | MRU% |
|------|-----|-----------|------|------|
| **Ours** | **93.2** | **101.8** | **72.6** | **80.1** |
| Pathfinder | 90.6 | 109.7 | 69.4 | 77.3 |
| G-safeguard | 89.4 | 113.2 | 68.1 | 76.0 |
| Robin | 88.1 | 117.9 | 66.5 | 74.6 |
| Masrouter | 86.9 | 121.4 | 64.8 | 73.2 |

**Footer**: KU=知识更新追踪, MS=跨会话聚合, TR=时序推理 | SR=任务成功率, MRU=记忆利用率

---

### Page 10 — 消融分析与深度讨论
**Template**: `templates/03_content.svg`
**Layout**: Two-column cards + embed image
**Key Message**: 事件历法是 Chronos 最核心组件（移除后准确率下降34.5pp）；记忆容量存在最优区间

**Left Card — Chronos 消融（Low配置）**:

| 移除组件 | 性能下降 |
|---------|---------|
| 事件历法索引 | **−34.5pp** |
| 初始检索 | −14.3pp |
| 动态提示 | −12.6pp |
| Reranking | −9.2pp |
| 日期过滤 | −9.2pp |

> 事件历法单独贡献：基线 +58.9%

**Right Column**:
- embed `chronos_error_analysis.png` (Chronos High vs Low 错误类型)
- **关键洞察**: 检索失败仍是最大错误类别；高性能模型（Opus 4.6）将计算/计数错误减半
- embed mini chart concept for `cognitive_entropy.png` (熵系数-性能关系)
- **记忆容量结论**: 过大的记忆空间引入检索噪声，适中容量下推理最稳定

**Footer**: Chronos消融: 116题分层样本 | 认知建模: WebShop全量评测

---

### Page 11 — 局限性与挑战
**Template**: `templates/03_content.svg`
**Layout**: Two-column (left: Chronos; right: 认知建模) + bottom synthesis
**Key Message**: 两种框架共同面临存储开销、推理计算成本和大规模扩展性三大挑战

**Left — Chronos 局限** [icon: tabler-outline/alert-triangle]:
1. **存储开销**: 双索引（对话历法 + 事件历法）存储量高于纯对话系统
2. **离线提取成本**: LLM驱动的事件提取在摄入阶段引入额外计算
3. **并行检索复杂度**: 查询时双路召回增加推理延迟，制造吞吐量-准确率权衡
4. **偏好召回偏弱**: SSP类别仍落后Honcho 10pp，需专项优化

**Right — 认知建模局限** [icon: tabler-outline/alert-triangle]:
1. **记忆容量敏感性**: 性能对K值非线性，工程部署中超参调优成本高
2. **可解释性不足**: 注意力驱动记忆检索的内部机制难以直接解读
3. **评测范围受限**: 仅在WebShop单一数据集上验证，跨领域泛化未评估
4. **安全/资源约束缺失**: 未引入实际部署中的安全限制与资源约束

**Bottom Synthesis**:
> **共同挑战**: 结构化记忆的精确性 vs 检索成本的权衡 · 长期运行中记忆的老化与更新策略 · 多用户/多Agent共享记忆场景的扩展性

**Footer**: 局限性分析对应综合研究方向：高效记忆操作 · 自适应记忆更新 · 记忆驱动安全决策

---

### Page 12 — 综合结论与展望
**Template**: `templates/04_ending.svg`
**Layout**: Single column centered + cards

- **感谢语**: 感谢聆听，欢迎交流与指正
- **副标题**: LLM 长期记忆机制：结构化时序 × 认知闭环，双路径逼近持续智能

**Three Takeaway Cards**:
1. **核心贡献共识** — 结构化记忆（事件历法 / 记忆模块）比纯向量检索具有本质优势；Chronos 在对话记忆 SOTA，认知建模在长程决策 SOTA
2. **方法论互补** — 对话侧强调"时序精度与动态检索"；决策侧强调"感知-推理-决策闭环"；两者共同指向"记忆与推理的深度耦合"
3. **未来方向** — 持续学习中的记忆老化策略 · 多智能体共享记忆架构 · 认知建模在LLM对话场景的迁移 · 更高效的记忆操作（减少检索噪声）

**Footer**: arXiv:2603.16862 (Chronos, 2026) | preprints202602.1990 (Yang et al., 2026)

---

## X. Speaker Notes Requirements

| Property | Value |
|----------|-------|
| **File naming** | Match SVG names: `01_封面.md`, `02_目录.md` … |
| **Master doc** | `notes/total.md` (with `#` headings, `---` separators) |
| **Split files** | `notes/` (NO `#` heading lines in split files) |
| **Content style** | 口语化中文，每页100–200字，讲综述内容 |
| **Structure** | `[过渡]` 开头（首页除外）+ 要点说明 + `要点：①②③` + `时长：X分钟` |
| **Total duration** | 约20分钟（含问答缓冲） |
| **Purpose** | 学术汇报 — 传递研究进展与思考 |

---

## XI. Technical Constraints Reminder

1. viewBox: `0 0 1280 720` — MANDATORY
2. No `<style>`, `class`, `foreignObject`, `clipPath`, `mask`, `animate*`, `textPath`
3. Text wrapping: use `<tspan>` only, never `<foreignObject>`
4. Transparency: `fill-opacity` / `stroke-opacity` only — never `rgba()`
5. Arrows: `<polygon>` triangles — never `<marker>`/`marker-end`
6. No `<g opacity="...">` (group opacity) — apply opacity to individual child elements
7. Images: `<image href="../images/xxx.png" preserveAspectRatio="xMidYMid meet"/>`
8. Icons: `<use data-icon="tabler-outline/brain" x="..." y="..." width="32" height="32" fill="#0066CC"/>`
9. Font: `font-family="Microsoft YaHei, 微软雅黑, Arial, sans-serif"` on all text
10. Inline styles only — no external CSS, no `@font-face`

---

## XII. Design Checklist

### Before Generation
- [x] Content outline reviewed and page assignments confirmed
- [x] Color scheme confirmed: #003366 primary + #E87722 orange accent
- [x] Image files confirmed in `images/` directory
- [x] Icon library locked: `tabler-outline`
- [x] Font plan confirmed: Microsoft YaHei, body 17px

### After Generation
- [ ] All 12 SVGs present in `svg_output/`
- [ ] viewBox = `0 0 1280 720` on every page
- [ ] Orange (#E87722) replaces red for left decorative bars
- [ ] No prohibited SVG elements
- [ ] Text readable (≥12px minimum)
- [ ] Content within safe area
- [ ] `notes/total.md` generated

---

## XIII. Next Steps

> Image approach: Existing images only (no AI generation) → **Proceed directly to Executor**

**Executor style**: `executor-consultant.md` (General Consulting — data-first, structured academic)

Read:
1. `references/executor-base.md` ✅ (already read)
2. `references/executor-consultant.md` → then generate all 12 SVGs sequentially
