# 模块 5：🎙️ 播客脚本 + 音频生成

将论文转化为可直接播出的播客内容，结合 edge-tts MCP 生成 MP3 音频文件。

---

## 第零步：加载并检测 edge-tts MCP 是否可用

**在询问任何播客形式之前，必须先完成此检测。**

### 0a. 加载 MCP 工具定义

edge-tts 是延迟加载工具（deferred tool），**必须先调用 `tool_search` 加载工具定义，才能使用**。

```
tool_search(query="edge-tts list voices")
```

> ⚠️ 如果跳过此步骤直接调用 `edge-tts:list_voices`，会因为工具未加载而失败。

### 0b. 检测 MCP 连接状态

加载成功后，尝试调用 `edge-tts:list_voices` 工具（无参数）：

- ✅ **调用成功** → MCP 已连接，正常进入第一步，告知用户"🎙️ edge-tts 已就绪，可以直接生成音频"
- ❌ **调用失败 / 工具不存在** → MCP 未连接，输出以下安装引导后**仍继续执行**（降级为纯文字脚本模式）：

---

### MCP 未连接时的提示内容

> ⚠️ **未检测到 edge-tts MCP，本次只能输出文字脚本。**
>
> 如需生成 MP3 音频，请按以下步骤安装：
>
> **第一步：确认 `uvx` 已安装**
> ```bash
> which uvx
> ```
> 没有输出？运行以下命令安装：
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```
>
> **第二步：在 Claude Desktop 配置文件中添加以下内容**
>
> 配置文件路径：
> - macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`
> - Windows：`%APPDATA%\Claude\claude_desktop_config.json`
>
> 在 `mcpServers` 中添加：
> ```json
> "edge-tts": {
>   "command": "/替换为uvx完整路径/uvx",
>   "args": ["better-tts-mcp"]
> }
> ```
> > 💡 用 `which uvx` 的输出替换上方路径，例如 `/Users/yourname/.local/bin/uvx`
>
> **第三步：重启 Claude Desktop，重新打开对话即可。**
>
> ---
> 现在继续为你生成文字脚本，安装完成后重新运行即可直接生成音频 👇

---

## 第一步：询问播客形式和输出目录

> "需要哪种播客形式？
> A) 🎤 单人解说（主播独白，科普风格，适合个人播客）
> B) 🎭 双人对话（主持人 × 研究员，问答互动，更有代入感）
>
> 时长偏好？
> - 短版（约5分钟，800-1000字脚本）
> - 长版（约12分钟，2000-2500字脚本）
>
> 音频保存到哪个目录？请给出完整绝对路径，例如 `/Users/你的用户名/Desktop`。不指定则默认 `/tmp`。"

若用户未指定形式，默认：双人对话 + 短版。
若用户未指定目录，默认：`/tmp`（生成后提供 `cp` 命令方便移动）。

---

## 第二步：构建播客内容骨架

播客必须覆盖以下核心维度，**按重要性排序**从 PAPER_CORE 取材：

| 播客段落 | 来源字段 | 重要性 |
|---------|---------|--------|
| 开场钩子 | `fun_fact` / `one_liner` | ⭐⭐⭐ 必须有冲击力 |
| 问题背景 | `problem` + `prior_work` | ⭐⭐⭐ 听众要先理解痛点 |
| 核心洞察 | `insight` + `hypothesis` + `analogy` | ⭐⭐⭐ 播客灵魂所在 |
| 方法解读 | `method` + `key_modules` | ⭐⭐ 口语化，不讲公式 |
| 关键结果 | `result` + `ablation` | ⭐⭐⭐ 数字要有对比语境 |
| 意义与展望 | `significance` + `future_work` | ⭐⭐ 给听众留下思考 |
| 局限性 | `limitation` + `failure_case` | ⭐ 增加可信度，不回避 |

> ⚠️ 播客写作铁律：
> - **禁止公式**，所有数学表达转为口语类比
> - **禁止列表朗读**，改为自然过渡句
> - 每个数字都要有对比语境："比之前最好的方法高了3%，相当于…"
> - `analogy` 字段是核心武器，必须用上
> - `fun_fact` 优先放开场，没有则从 `result` 里找最反直觉的发现

---

## 第三步A：单人解说脚本格式

```
[片头音乐提示：3秒]

[开场 - 30秒]
大家好，欢迎收听。今天我们聊一篇让我眼前一亮的论文——
[PAPER_CORE.one_liner 的口语化版本]
[PAPER_CORE.fun_fact 或最反直觉的发现，制造悬念]

[问题背景 - 60秒]
在聊这篇论文之前，我们先搞清楚它在解决什么问题。
[PAPER_CORE.problem 的口语化展开]
[PAPER_CORE.prior_work 的现有方法局限，1-2句]
所以，有没有更好的办法？这篇论文给出了一个很有意思的答案。

[核心方法 - 90秒]
他们的核心思路是这样的——
[PAPER_CORE.analogy 完整展开，先讲类比再讲技术]
具体来说，[PAPER_CORE.method 的口语化步骤，3-4步，每步一句]
其中最关键的一个设计是 [PAPER_CORE.key_modules 中最重要的一个，口语化解释]

[实验结果 - 60秒]
那效果怎么样？
[PAPER_CORE.result 中最重要的1-2条，数字+对比语境]
他们还做了一个很有意思的实验：[PAPER_CORE.ablation 的口语化描述]

[意义与局限 - 40秒]
这项工作的价值在于——[PAPER_CORE.significance]
当然，它也有局限：[PAPER_CORE.limitation，1句，客观]

[结尾 - 20秒]
好了，这就是今天的内容。用一句话总结这篇论文：
[PAPER_CORE.one_liner]
感兴趣的朋友可以搜索原文 [PAPER_CORE.title]。我们下期再见。

[片尾音乐提示：3秒]
```

**时长控制**：短版输出开场+问题背景+核心方法+结果+结尾；长版全部段落展开。

---

## 第四步B：双人对话脚本格式

角色设定：
- **主持人（Host）**：好奇心强的技术爱好者，代表听众提问，用 [H] 标注
- **研究员（Expert）**：论文领域专家，负责深度解释，用 [E] 标注

```
[H] 开场白 + 引出论文话题（用 fun_fact 或反直觉问题制造悬念）

[E] 接梗，简短确认这个研究方向的有趣之处

[H] "那在这篇论文出来之前，大家是怎么处理这个问题的？"

[E] 介绍 prior_work，指出核心痛点（口语，具体）

[H] "所以这篇论文的思路是什么？用普通人能理解的方式说说？"

[E] 用 analogy 解释，再逐步引入 method（先类比后技术）

[H] 提出一个听众会有的疑问（来自 PAPER_CORE.hypothesis 或 key_modules 中最难理解的部分）

[E] 回答，可适当补充 key_modules 细节

[H] "那实验结果呢？真的比之前的方法好吗？"

[E] 报告 result（最重要的1-2个数字），给出对比语境，引用 ablation 的有趣发现

[H] "听起来很厉害，那有没有什么局限性？做不到的事情？"

[E] 客观说明 limitation 和 failure_case，体现学术诚实

[H] "最后，你觉得这个工作最值得关注的地方是什么？"

[E] 总结 significance + future_work，用 one_liner 收尾

[H] 感谢 + 片尾语
```

**双人对话原则**：
- [H] 的问题必须是听众真实会有的疑问，不能是"请介绍一下方法"这种串词
- [E] 的每段回答不超过100字，保持对话节奏
- 全程禁止出现"首先、其次、最后"这种列举式语气
- 对话要有来回，[H] 可以追问、表示惊讶、打断补充

---

## 第五步：生成音频（MCP 可用时执行）

> ⚠️ 若第零步检测到 MCP 不可用，跳过本步骤，直接输出文字脚本并附上安装提示。

### ⚠️ output_dir 关键说明（必读）

edge-tts MCP 运行在**用户本地机器**上，写文件时路径是用户本地的文件系统路径，
**不是** Claude 云端容器的路径（如 `/mnt/user-data/outputs` 或 `/home/claude`）。

**必须在生成前向用户询问输出目录**，示例话术：

> "请告诉我音频保存到哪个目录？请给出**完整绝对路径**，例如：
> - macOS：`/Users/你的用户名/Desktop`
> - Windows：`C:\Users\你的用户名\Desktop`
>
> 如果不确定，我会默认保存到 `/tmp`，生成后你可以手动移动。"

**路径使用规则：**
1. **用户提供了路径** → 直接使用（必须是绝对路径）
2. **用户说"默认"或不想指定** → 使用 `/tmp`，生成后提供 `cp` 命令
3. **如果用户记住了路径** → 可以通过 memory_user_edits 工具记住，下次自动使用

**❌ 绝对不要使用以下路径**（会报 Read-only filesystem 或 Permission denied）：
- `.`（当前目录，MCP 进程的 cwd 可能只读）
- `~/Desktop`、`~/Downloads`（`~` 波浪号不会被 MCP 展开，必须用完整路径如 `/Users/xxx/Desktop`）
- `/mnt/...`、`/home/claude/...`（云端容器路径，MCP 无法访问）
- `/Users`（根目录无写权限，必须到具体用户子目录）

### 单人音频（调用 edge-tts:text_to_speech）

```
voice: zh-CN-YunxiNeural（男声科普风）或 zh-CN-XiaoxiaoNeural（女声）
rate: +5%（略快，播客节奏）
output_dir: /tmp（默认），或用户指定的本地路径
```

输出文件命名建议：`podcast_[论文简称]_[日期].mp3`

### 双人音频（调用 edge-tts:text_to_speech_multi_voice）

Marker 格式：
```
[zh-CN-YunxiNeural]（主持人台词）
[zh-CN-XiaoxiaoNeural]（研究员台词）
```

推荐声音搭配：
- 主持人 [H]：`zh-CN-YunxiNeural`（男声，自然活泼）
- 研究员 [E]：`zh-CN-XiaoxiaoNeural`（女声，沉稳专业）
- 或反过来，根据用户偏好调整

### 生成前确认

向用户展示：
> "准备生成音频：
> - 形式：[单人/双人]
> - 预估时长：[X] 分钟
> - 保存位置：[用户指定的路径 或 /tmp]
> 确认生成？"

---

## 第六步：生成完成后

提示用户：
> "🎙️ 播客已生成：[文件路径]
> 还需要以下配套内容吗？
> - 📝 文字稿（方便发布到播客平台）
> - 📢 宣传推文（模块 4）
> - 🧠 配套思维导图（模块 2，可作为封面/配图）"

---

## 质量检查清单

生成脚本前自查：
- [ ] `analogy` 已使用（播客灵魂）
- [ ] `fun_fact` 或反直觉发现在开场（抓住听众）
- [ ] 所有数字有对比语境
- [ ] 无公式，无列表式朗读
- [ ] `limitation` 被诚实提及（增加可信度）
- [ ] 全文无"首先其次最后"式串联
- [ ] 双人对话中 [H] 的问题是真实听众问题
