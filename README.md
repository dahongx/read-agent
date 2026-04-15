# 文献阅读 Agent

一个面向学术汇报场景的单篇论文阅读 Agent。

当前版本已经打通这条主流程：

`上传 PDF -> 生成 PPT -> 生成讲稿 -> 展示幻灯片 -> 论文问答 -> 原文页码跳转`

## 当前能力

- 上传单篇论文 PDF
- 调用 Claude CLI 执行 `paper-to-ppt` skill 生成 PPT
- 输出 SVG 幻灯片、PPTX 文件和逐页讲稿
- 基于论文内容构建 RAG 索引并支持问答
- 回答内带页码引用，点击可跳转原文
- 支持语音输入提问与浏览器 TTS 朗读

## 项目结构

- `backend/` FastAPI 后端、任务编排、RAG、PPT 生成接入
- `frontend/` React + Vite 前端
- `openspec/` 需求与迭代记录
- `.claude/skills/` 本项目依赖的 Claude Code skills

## 运行前准备

需要以下环境：

- Python 3.10+
- Node.js 18+
- Claude Code CLI，并且本机已可执行 `claude`
- 可用的 LLM API Key

## 配置

1. 复制 `backend/.env.example` 为 `backend/.env`
2. 按实际环境填写关键变量：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `SKILL_DIR`
- `CLAUDE_CLI_PATH`，如果 `claude` 不在 PATH 中
- `GIT_BASH_PATH`，如果 Windows 下 Claude CLI 需要显式指定 Git Bash

默认情况下，项目会优先按相对路径查找：

- `SKILL_DIR=.claude/skills/paper-to-ppt`
- `UPLOAD_DIR=backend/uploads`
- `PPT_CACHE_DIR=backend/uploads/ppt_cache`

## 启动方式

### 生产模式

在 `backend/` 目录运行：

```bat
start_prod.bat
```

这个脚本会：

- 检查 `backend/.env`
- 如果前端还没构建，则先执行 `npm install` 和 `npm run build`
- 启动 FastAPI，并同时托管前端静态页面

启动后访问：

`http://localhost:8000`

### 开发模式

在 `backend/` 目录运行：

```bat
start.bat
```

## 发布说明

仓库已经忽略以下本地产物，不会再被提交：

- `backend/.env`
- `backend/uploads/`
- `projects/`
- `output/`
- `paper/`
- `frontend/node_modules/`
- `frontend/dist/`

这些目录都是本地运行缓存、测试产物或构建结果。

## 当前定位

当前版本是 **单篇论文 MVP**，重点是把单篇上传、生成和问答链路跑通并稳定下来。

后续规划见：

- `版本规划.md`
- `v1.0-report.md`
- `PRD.md`