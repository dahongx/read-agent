## Problem

当前 web agent 的 PPT 生成是 stub（假数据），始终展示同一套 fixture PPT，与用户上传的 PDF 无关。

## Solution

将已验证可用的本地 `paper-to-ppt` skill 流程（paper-glance → ppt-master）集成到 web agent 后端，作为真实的 PPT 生成任务。

用户在上传 PDF 时选择 PPT 配置（模板 + 八项参数），后端以 PDF 内容哈希 + 配置哈希作为缓存 key，相同输入直接复用已生成的项目目录，不重复调用 LLM。

## Goals

- 上传任意 PDF → 生成真实对应的 PPT（SVG slides + PPTX + speaker notes）
- 配置选择在上传页面完成，后台全自动生成，无需交互
- 相同 PDF + 相同配置 → 命中缓存，秒级响应
- 去掉所有 DEV_MODE 预设（DEV_MODE=false 成为默认）
- 生成完成后展示 PPT + 问答，全部基于真实 PDF 内容

## Non-Goals

- AI 图片生成（image_gen.py）— 保持"不生成AI图片"选项
- 多 PDF 联合问答 — 本期只做单文档
