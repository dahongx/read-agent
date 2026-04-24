---
name: paper-to-ppt
description: >
  文献汇报全流程自动化。当用户说"帮我把这篇论文做成PPT"、"paper to ppt"、
  "文献汇报"、"论文PPT"、提供PDF文件并提到PPT时触发。
  流程：paper-glance深度解析 → ppt-master生成演讲PPT（含speaker notes）→ 导出PPTX。
---

# Paper to PPT — 文献汇报全流程 Skill

## 🎯 目标
将学术论文 PDF 自动转化为可用于课堂汇报的演讲 PPT（含每页演讲稿），用户只需在两个关键节点做选择。

---

## 批量模式（Batch Mode）

**检测条件**：如果用户消息中包含以下任意标记，则进入批量模式：
- `[BATCH_MODE]`
- 消息中同时包含"模板："和"页数："和"风格："

**批量模式行为**：
- 跳过所有 `⛔ BLOCKING` 交互点，直接使用消息中提供的配置值
- 不调用 AskUserQuestion 工具
- 全自动执行完整流程直到输出 PPTX

---

## 执行规则

1. **串行执行**：paper-glance 分析完成后再启动 ppt-master，不并行
2. **两个用户交互点**：模板选择 + 八项确认，其余全部自动执行（批量模式下跳过）
3. **中文输出**：分析报告和PPT内容均使用中文，专业术语保留英文
4. **speaker notes 必须生成**：每一页PPT都要有演讲稿，供TTS朗读使用
5. **阶段标记必须输出**：为便于后端定位卡点，在批量模式下必须在关键节点原样输出单独一行 marker：
   - `[[P2P_PHASE:paper_glance_started]]`
   - `[[P2P_PHASE:paper_glance_completed]]`
   - `[[P2P_PHASE:ppt_master_started]]`
   marker 必须单独成行，不要加解释文字，不要改写大小写。

---

## 流程

### 阶段一：paper-glance 论文解析（全自动）

进入本阶段后，先输出单独一行：`[[P2P_PHASE:paper_glance_started]]`

读取用户提供的 PDF，按以下结构在内部构建 PAPER_CORE（不展示给用户），然后生成**深度分析报告 Markdown**，包含：

- 摘要中文翻译
- 方法动机（为什么做、现有痛点、核心假设）
- 方法设计（Pipeline、核心模块、关键公式）
- 与其他方法对比（含对比表格）
- 实验表现（数据具体，有数字）
- 总结（一句话核心思想 + 速记Pipeline）

> 分析完成后，先输出单独一行：`[[P2P_PHASE:paper_glance_completed]]`
> 然后告知用户："✅ 论文解析完成，正在进入PPT生成阶段..."

---

### 阶段二：ppt-master PPT生成

进入本阶段后，先输出单独一行：`[[P2P_PHASE:ppt_master_started]]`

将阶段一的分析报告作为源内容，调用 ppt-master 完整流程：

**预设参数（自动应用，无需询问）：**
- 源内容：阶段一生成的分析报告 Markdown
- Canvas格式：ppt169（16:9）
- 目标受众：高校师生、学术汇报场景
- 语言：中文为主，术语保留英文
- 图片方案：不生成AI图片，使用文字+图表+数据可视化
- **Speaker notes**：每页必须生成，口语化中文，适合TTS朗读，100-200字/页

**用户交互点1 — 模板选择**：
- **批量模式**：直接使用消息中"模板："字段的值，跳过，不调用 AskUserQuestion
- **交互模式**：展示可用模板，推荐学术风格，等用户选择（⛔ BLOCKING）

**用户交互点2 — 八项确认**：
- **批量模式**：直接使用消息中提供的页数/语言/风格/受众值，其余项用默认值，跳过，不调用 AskUserQuestion
- **交互模式**：展示以下推荐值，用户可修改（⛔ BLOCKING）：
  1. Canvas格式：ppt169
  2. 页数：12-15页
  3. 目标受众：高校师生
  4. 风格：学术专业，逻辑清晰
  5. 配色：蓝白为主，橙色强调
  6. 图标：适量线条图标
  7. 字体：标题大字加粗，正文14-16pt
  8. 图片：无AI生成图，数据图表为主

**输出路径**：`E:\agent\reading agent\output\<论文标题简写>_presentation.pptx`

---

## 完成提示

PPT 生成后告知用户：
- PPTX 文件路径
- 总页数
- 提醒：每页 speaker notes 已生成，可直接用于 TTS 朗读
