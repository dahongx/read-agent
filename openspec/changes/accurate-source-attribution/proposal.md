## Problem
RAG 检索的 top-k chunks 作为来源展示，但 LLM 回答时可能只用到其中部分 chunk，导致：
1. 参考文献页（第12页）被检索到并展示为来源，与答案无关
2. 来源页码与答案实际出处不匹配，用户点击"第N页"跳到的是噪声页

## Solution
本地测试（test_qa.py）已验证：
1. 加强 prompt 要求 LLM 在答案中插入 `(第N页)` 标注 → LLM 能稳定遵从
2. 解析答案中的页码 → 来源只含 LLM 实际引用的页，噪声页自动消失
3. 参考文献页（大量 arXiv/doi/年份行）在建索引时直接过滤 → 从根源减少噪声

## Validated Locally
test_qa.py 测试"这篇论文的创新点是什么"：
- 检索页: [1, 6, 7, 9, 12, 14]  → 第12页是噪声
- LLM 引用页 (V2 prompt): [1, 14, 7, 6, 9] → 第12页未被引用
- 结论：citation-based sources 显著优于 top-k sources
