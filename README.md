# 文献阅读 Agent

一个面向学术汇报场景的单篇论文阅读 Agent。

当前版本已经打通这条主流程：

`上传 PDF -> 生成 PPT -> 生成讲稿 -> 展示幻灯片 -> 论文问答 -> 原文页码跳转`

## 当前能力

- 上传单篇 / 多篇论文 PDF
- 调用 Claude CLI 执行 `ppt-master` skill 生成 PPT（含 PDF→Markdown、图片抽取、SVG 排版、PPTX 导出）
- 输出 SVG 幻灯片、PPTX 文件和逐页讲稿
- 基于论文内容构建 RAG 索引并支持问答（BGE-m3 + LlamaIndex VectorIndexRetriever）
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

- `SKILL_DIR=.claude/skills/ppt-master`
- `UPLOAD_DIR=backend/uploads`
- `PPT_CACHE_DIR=backend/uploads/ppt_cache`

> `.claude/skills/paper-to-ppt` 和 `.claude/skills/paper-glance-skill` 是早期实现，
> 当前后端已不再调用它们。可以保留作为参考，也可以直接删除以避免误用。

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

### 终端调试 RAG 问答

不启动前端就想看 RAG 检索质量 / 引用 quote / 命中页码：

```bat
cd backend
python chat_cli.py --pdf path/to/paper.pdf
```

参数：
- `--pdf <path>` 指定 PDF；首次会建索引到 `backend/uploads/cache/rag/<sha>-cli/`
- `--index <dir>` 复用已有索引目录（必须已含 `bm25_corpus.json`）
- `--question "..."` 单次问答，不进入交互
- `--quiet` 抑制 INFO 日志

每条问答会打印答案、`<CITATIONS>` 里的逐字 quote、quote 是否真的命中检索到的 chunk，以及 retrieve / LLM 各自耗时。

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