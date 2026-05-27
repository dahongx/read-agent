# 量子力学基础：定态与一维势阱 - Design Spec

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | quantum_lect4 |
| **Canvas Format** | PPT 16:9 (1280×720) |
| **Page Count** | 12页 |
| **Design Style** | General Versatile（教学讲义风格） |
| **Target Audience** | 高校师生（大学物理/量子力学课程） |
| **Use Case** | 课堂教学课件，教师上课使用 |
| **Template** | smart_red（几何商务风，适配教育场景） |
| **Created Date** | 2026-05-27 |

---

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280×720 px |
| **viewBox** | `0 0 1280 720` |
| **Margins** | 左右 60px，上下 50px |
| **Content Area** | x: 60–1220, y: 100–670 |
| **Title Area** | y: 50–105 |
| **Footer Area** | y: 680–720 |
| **Grid Baseline** | 40px |

---

## III. Visual Theme

### Theme Style

- **Style**: 教学讲义风格，几何线条装饰，卡片式内容布局
- **Theme**: 浅色主题（米白底 + 暖色调强调）
- **Tone**: 亲和、专业、清晰、现代

### Color Scheme

> 用户要求：米白底暖色调，避免黑底，配以蓝/绿/橙等亲和色彩强调

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#FDFAF5` | 页面背景（米白暖色） |
| **Secondary bg** | `#FFF8F0` | 卡片背景、区块背景 |
| **Primary Red** | `#DE3545` | 标题装饰、几何切角、重点强调 |
| **Accent Orange** | `#E8834A` | 次级强调、渐变配色、图标 |
| **Accent Blue** | `#2E86AB` | 公式框、概念图、知识点图标 |
| **Accent Green** | `#4CAF7D` | 正确示例、总结要点、练习题 |
| **Body text** | `#3D3530` | 正文主色（暖棕黑，非纯黑） |
| **Secondary text** | `#7A6E68` | 副标题、注释文字 |
| **Tertiary text** | `#A89E98` | 页码、补充信息 |
| **Border/divider** | `#E8DDD5` | 卡片边框、分割线（暖色调） |
| **Cover bg** | `#FDF6EC` | 封面背景（温暖米白，替代黑底） |
| **Formula bg** | `#EEF6FF` | 公式背景框（浅蓝） |

### Gradient Scheme

```xml
<!-- 封面标题装饰渐变 -->
<linearGradient id="coverAccent" x1="0%" y1="0%" x2="100%" y2="0%">
  <stop offset="0%" stop-color="#DE3545"/>
  <stop offset="100%" stop-color="#E8834A"/>
</linearGradient>

<!-- 几何装饰渐变 -->
<linearGradient id="geoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
  <stop offset="0%" stop-color="#DE3545" stop-opacity="0.9"/>
  <stop offset="100%" stop-color="#E8834A" stop-opacity="0.7"/>
</linearGradient>

<!-- 公式区背景 -->
<linearGradient id="formulaBg" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0%" stop-color="#EEF6FF"/>
  <stop offset="100%" stop-color="#E8F4FD"/>
</linearGradient>
```

---

## IV. Typography System

### Font Plan

**Recommended preset**: P1（现代教育/理工科）

| Role | Chinese | English | Fallback |
| ---- | ------- | ------- | -------- |
| **Title** | Microsoft YaHei | Arial | sans-serif |
| **Body** | Microsoft YaHei | Calibri | sans-serif |
| **Formula** | - | Consolas | Monaco |
| **Emphasis** | SimHei | Arial Black | sans-serif |

**Font stack**: `"Microsoft YaHei", Arial, "Helvetica Neue", sans-serif`

### Font Size Hierarchy

> 用户要求：标题大字加粗，正文14-16pt（约18-22px），比商务汇报放大一档

**Baseline**: Body font size = 22px（教学讲义宽松密度，3-5点/页）

| Purpose | Ratio | Size | Weight |
| ------- | ----- | ---- | ------ |
| Cover title | 3x | 66px | Bold |
| Cover subtitle | 1.8x | 40px | SemiBold |
| Page title | 2x | 44px | Bold |
| Section title | 1.5x | 33px | Bold |
| Card title | 1.3x | 28px | Bold |
| **Body content** | **1x** | **22px** | Regular |
| Formula text | 1x | 22px | Regular (Consolas) |
| Annotation | 0.8x | 18px | Regular |
| Page number | 0.6x | 14px | Regular |

---

## V. Layout Principles

### Page Structure

- **Header area**: y=0–90，导航栏 + 页面标题 + 红色几何装饰
- **Content area**: y=100–665，主内容区（卡片/图表/公式）
- **Footer area**: y=670–720，页码 + 课程名称

### Common Layout Modes

| Mode | Suitable Scenarios |
| ---- | ----------------- |
| **单列居中** | 封面、总结、章节过渡页 |
| **左右分栏 (5:5)** | 对比分析、概念对比 |
| **左右分栏 (4:6)** | 图示+文字说明 |
| **三列卡片** | 特征列举、步骤说明 |
| **上下分区** | 公式+解释，题目+解答 |
| **大卡片+侧边** | 例题精讲、重点公式 |

### Spacing Specification

| Element | Current Project |
| ------- | --------------- |
| Card gap | 24px |
| Content block gap | 32px |
| Card padding | 28px |
| Card border radius | 8px |
| Icon-text gap | 12px |
| Single-row card height | 540px |
| Double-row card height | 255px each |
| Three-column card width | 360px each |

---

## VI. Icon Usage Specification

### Source

- **Library**: `tabler-outline`（线条风格，适合教学场景的轻盈美感）
- **Usage method**: Placeholder format `{{icon:tabler-outline/icon-name}}`

### Icon Inventory

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| 量子/原子概念 | `tabler-outline/atom` | 封面、导入页 |
| 波函数 | `tabler-outline/wave-sine` | 新知4、新知6 |
| 学习目标 | `tabler-outline/target` | 学习目标页 |
| 关键洞察/灵感 | `tabler-outline/bulb` | 导入页、总结页 |
| 理解/思考 | `tabler-outline/brain` | 导入页 |
| 数学公式 | `tabler-outline/math-function` | 新知1、新知2 |
| 积分符号 | `tabler-outline/math-integral` | 新知6 |
| 总结清单 | `tabler-outline/checklist` | 总结页 |
| 练习/思考题 | `tabler-outline/question-mark` | 练习页 |
| 书写/练习 | `tabler-outline/pencil` | 例题、练习页 |
| 折线图/图像 | `tabler-outline/chart-line` | 新知6 |
| 物理实验 | `tabler-outline/flask` | 导入页 |
| 教材参考 | `tabler-outline/book` | 总结页 |
| 完成/正确 | `tabler-outline/circle-check` | 例题解答 |
| 警告/易错 | `tabler-outline/pencil-exclamation` | 例题易错点 |

---

## VII. Chart Reference List

| Chart Type | Purpose | Used In |
| ---------- | ------- | ------- |
| 能级图（自绘SVG竖向条形） | 展示量子化能级 E₁, E₂, E₃... | 新知5（能量量子化） |
| 波函数图（折线/正弦曲线SVG） | ψ₁, ψ₂, ψ₃ 及其概率密度 | 新知6（波函数） |
| 对比表格 | 经典粒子 vs 量子粒子 | 导入页 |
| 步骤流程图（横向箭头） | 解题步骤 | 例题精讲 |

---

## VIII. Image Resource List

> 用户要求：不生成AI图片，使用文字+图表+数据可视化

无需AI生成图片，所有视觉内容通过SVG图形、公式框、图表实现。

---

## IX. Content Outline

### Part 1: 开场（2页）

#### Slide 01 - 封面

- **Layout**: 几何装饰 + 居中标题（smart_red封面风格，米白底替代黑底）
- **Title**: 量子力学基础
- **Subtitle**: 定态与一维无限深方势阱
- **Info**: 第4讲 · 大学量子力学
- **Design**: 左上角红色三角切角 + 右下角橙色三角切角（替代原黑色为暖色），中央标题区域

#### Slide 02 - 学习目标

- **Layout**: 单列居中，四个目标卡片（2×2网格）
- **Title**: 本讲学习目标
- **Content**:
  - 🎯 能说出定态的定义及其三个核心特征
  - 🎯 能解释为什么定态的概率密度不随时间变化
  - 🎯 会运用分离变量法推导定态薛定谔方程
  - 🎯 会判断无限深方势阱中粒子的允许能级与波函数
- **Icon**: `tabler-outline/target`

### Part 2: 课堂导入（1页）

#### Slide 03 - 课堂导入：经典 vs 量子

- **Layout**: 左右对比（5:5），中间分割线
- **Title**: 一个粒子被"关"在盒子里，会发生什么？
- **Content**:
  - 左列（经典粒子）：任意速度 → 任意能量 → 连续运动
  - 右列（量子粒子）：只允许特定能量 → 驻波 → 量子化
- **Chart**: 对比表格
- **Icon**: `tabler-outline/brain`, `tabler-outline/atom`
- **Design**: 左列用暖灰色背景，右列用浅蓝背景，突出对比

### Part 3: 新知讲解（6页）

#### Slide 04 - 新知1：分离变量法

- **Layout**: 上下分区（公式区 + 解释区）
- **Title**: 如何求解含时薛定谔方程？
- **Content**:
  - 核心思路：假设 Ψ(r,t) = ψ(r)·f(t)（变量分离）
  - 代入薛定谔方程后，左边只含 t，右边只含 r
  - 两边必须等于同一常数 E（分离常数 = 能量）
  - 公式框：iℏ df/dt = Ef(t) → f(t) = e^(-iEt/ℏ)
- **Icon**: `tabler-outline/math-function`
- **Design**: 公式用浅蓝背景框（#EEF6FF）突出显示

#### Slide 05 - 新知2：定态薛定谔方程

- **Layout**: 大卡片居中，公式突出
- **Title**: 定态薛定谔方程（时间无关）
- **Content**:
  - 核心方程：Ĥψ(r) = Eψ(r)
  - 展开形式：[-ℏ²/2m ∇² + V(r)]ψ(r) = Eψ(r)
  - 三个关键词：本征方程 / 本征值 E / 本征函数 ψ_E
  - 类比：就像"找到系统的固有振动模式"
- **Icon**: `tabler-outline/math-function`
- **Design**: 方程用大号字体（28px）居中展示，红色下划线装饰

#### Slide 06 - 新知3：定态的三个特征

- **Layout**: 三列卡片
- **Title**: 为什么叫"定态"？
- **Content**:
  - 卡片1（蓝色）：概率密度不变 |Ψ(r,t)|² = |ψ(r)|²，与时间无关
  - 卡片2（绿色）：能量确定 ⟨H⟩ = E，σ_H = 0
  - 卡片3（橙色）：任意力学量期望值不随时间变化
- **Icon**: `tabler-outline/wave-sine`
- **Design**: 三列卡片分别用蓝/绿/橙色顶部色条区分

#### Slide 07 - 新知4：无限深方势阱模型

- **Layout**: 左右分栏（4:6），左侧势能图，右侧文字
- **Title**: 最简单的量子模型：粒子在盒子里
- **Content**:
  - 左侧：势能函数图（V=0, 0<x<a；V=∞, x≤0或x≥a）
  - 右侧：
    - 物理图像：粒子被完全限制在 [0, a] 内
    - 边界条件：ψ(0) = 0，ψ(a) = 0
    - 盒内方程：ψ'' + k²ψ = 0，k = √(2mE)/ℏ
    - 通解：ψ(x) = A sin(kx + δ)
- **Icon**: `tabler-outline/flask`
- **Design**: 左侧势能图用SVG折线绘制（红色竖线表示无限高墙）

#### Slide 08 - 新知5：能量量子化

- **Layout**: 上下分区（公式 + 能级图）
- **Title**: 能量为什么只能取特定值？
- **Content**:
  - 边界条件 → sin(ka) = 0 → k = nπ/a（n = 1,2,3...）
  - 能级公式：E_n = n²π²ℏ²/(2ma²) = n²E₁
  - 基态能量 E₁ > 0（零点能，不为零！）
  - 能级图：竖向展示 E₁, E₂=4E₁, E₃=9E₁...
- **Chart**: 能级图（自绘SVG）
- **Icon**: `tabler-outline/chart-line`
- **Design**: 能级用橙色横线标注，n值用红色标注

#### Slide 09 - 新知6：波函数与正交归一性

- **Layout**: 左右分栏（5:5），左侧波函数图，右侧性质列表
- **Title**: 每个能级对应一个波函数
- **Content**:
  - 左侧：ψ₁, ψ₂, ψ₃ 及 |ψ|² 图像（SVG绘制正弦曲线）
  - 右侧：
    - 归一化：A = √(2/a)
    - 正交归一：∫ψ_m* ψ_n dx = δ_mn
    - 完备性：任意函数可展开 f(x) = Σ c_n ψ_n(x)
    - 展开系数：c_n = ∫ψ_n*(x)f(x)dx
- **Chart**: 波函数图（SVG正弦曲线）
- **Icon**: `tabler-outline/wave-sine`, `tabler-outline/math-integral`

### Part 4: 例题精讲（1页）

#### Slide 10 - 例题精讲

- **Layout**: 上下分区（题目 → 解题步骤 → 易错点）
- **Title**: 例题：求展开系数 c_n
- **Content**:
  - 【题目】已知 t=0 时 Ψ(x,0) = Ax(a-x)，求归一化常数 A 及展开系数 c_n
  - 【解题步骤】
    - Step 1：归一化 → A = √(30/a⁵)
    - Step 2：c_n = ∫ψ_n*(x)·Ax(a-x)dx
    - Step 3：计算积分 → n为偶数时 c_n = 0；n为奇数时 c_n = (8√15)/(nπ)³
  - 【易错点】n=0 不是有效量子数！最小值为 n=1
- **Icon**: `tabler-outline/pencil`, `tabler-outline/circle-check`, `tabler-outline/pencil-exclamation`
- **Design**: 易错点用红色背景框突出

### Part 5: 课堂练习 + 总结（2页）

#### Slide 11 - 课堂练习

- **Layout**: 两道练习题，上下排列
- **Title**: 课堂练习：请同学们思考
- **Content**:
  - 【练习1】若粒子处于叠加态 Ψ = (1/√2)ψ₁ + (1/√2)ψ₂，测量能量可能得到哪些值？各自概率是多少？
  - 【练习2】无限深方势阱中，基态能量 E₁ 与势阱宽度 a 的关系是什么？若 a 减小一半，E₁ 如何变化？
  - 提示：回顾 E_n = n²π²ℏ²/(2ma²)
- **Icon**: `tabler-outline/question-mark`
- **Design**: 绿色背景框，鼓励互动氛围

#### Slide 12 - 总结与作业

- **Layout**: 左右分栏（6:4），左侧关键词总结，右侧作业
- **Title**: 本讲小结
- **Content**:
  - 左侧关键词（对照学习目标）：
    - ✅ 定态 = 时间无关的概率分布
    - ✅ 定态薛定谔方程：Ĥψ = Eψ
    - ✅ 无限深方势阱：E_n = n²E₁，ψ_n = √(2/a)sin(nπx/a)
    - ✅ 能量量子化 + 零点能
    - ✅ 叠加态展开：Ψ = Σ c_n ψ_n
  - 右侧作业：
    - 课后习题：Griffiths 2.2, 2.3
    - 思考：为什么量子粒子不能静止？（零点能的物理意义）
- **Icon**: `tabler-outline/checklist`, `tabler-outline/book`

---

## X. Speaker Notes Requirements

- **File naming**: 与SVG文件名对应，如 `01_cover.md`
- **Total duration**: 约 45-50 分钟（标准一节课）
- **Notes style**: 第一人称课堂口吻，互动式
- **Presentation purpose**: 教学（instruct）
- **节奏标记**: 【提问】【停顿】【板书】【举例】【强调】
- **每页字数**: 200-350字
- **衔接语**: 每页必须有上下页衔接

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
8. Gradients defined in `<defs>`

### PPT Compatibility Rules:

- `<g opacity="...">` FORBIDDEN; set opacity on each child element individually
- Inline styles only; external CSS and `@font-face` FORBIDDEN
- 数学公式用文本近似表示（Unicode符号：ℏ ψ Ψ Σ ∫ δ π ∇ ²）

---

## XII. Design Checklist

### Pre-generation

- [x] 内容符合教学环节比例（封面+目标15%，导入8%，新知50%，例题8%，练习+总结17%）
- [x] 每页正文 ≤ 80字（新知讲解页）
- [x] 例题结构完整：题目→步骤→易错点
- [x] 至少1道课堂练习
- [x] 总结页对照学习目标

### Post-generation

- [ ] viewBox = `0 0 1280 720`
- [ ] 无 `<foreignObject>` 元素
- [ ] 所有文字可读（≥14px）
- [ ] 内容在安全区内
- [ ] 颜色符合规格（米白底，无黑底）
- [ ] 公式文字清晰可辨

---

## XIII. Next Steps

1. ✅ Design spec complete
2. **Next step**: 无AI图片 → 直接调用 **Executor** 角色生成SVG
