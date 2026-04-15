# 模块 2：思维导图

将论文核心结构可视化为思维导图，直接输出 Mermaid 代码块，无需任何 MCP 插件，Claude.ai 原生渲染。

---

## 默认输出：思维导图（mindmap）

**优先生成思维导图**，除非用户明确要求流程图。

直接输出 Mermaid mindmap 代码块：

````mermaid
mindmap
  root((**[论文简称]**))
    **问题**
      [现有方法痛点1]
      [现有方法痛点2]
    **方法**
      [核心模块1]
        [子组件]
      [核心模块2]
    **实验**
      [数据集名称]
      [关键结论 + 具体数字]
    **贡献**
      [创新点1]
      [创新点2]
    **局限**
      [局限性1]
````

生成后询问："需要再生成一张**方法流程图**吗？"

---

## 可选：方法流程图（Pipeline）

若用户需要，额外输出 Mermaid flowchart 代码块：

````mermaid
flowchart TD
    Input["📥 输入\n[输入数据类型]"]

    subgraph Method["[论文方法名称]"]
        Step1["[步骤1名称]\n[一句话描述]"]
        Step2["[步骤2名称]\n[一句话描述]"]
        Step3["[步骤3名称]\n[一句话描述]"]
    end

    Output["📤 输出\n[输出结果]"]
    Result["📊 关键结果\n[PAPER_CORE.result 关键数字]"]

    Input --> Step1 --> Step2 --> Step3 --> Output --> Result

    style Method fill:#e8f4f8,stroke:#2196F3
    style Result fill:#e8f5e9,stroke:#4CAF50
````

根据 `PAPER_CORE.method` 实际步骤数调整节点，用论文真实模块名称，中英文并排标注。

---

## 质量要求

- 所有节点文字必须来自论文原文，不捏造模块
- 数字来自 `PAPER_CORE.result`，不估算
- 中英文并排：`注意力机制 / Attention`
- 思维导图叶子节点控制在 10 字以内
- 输出为标准 Mermaid 代码块，用户也可复制到 mermaid.live 进一步编辑
