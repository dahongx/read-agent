@echo off
title 文献阅读 Agent
cd /d "%~dp0"
if not defined PYTHON_EXE (
    if exist "D:\program\anaconda3\envs\pocket-souls\python.exe" (
        set "PYTHON_EXE=D:\program\anaconda3\envs\pocket-souls\python.exe"
    ) else (
        set "PYTHON_EXE=python"
    )
)

echo ==============================
echo  文献阅读 Agent
echo  http://localhost:8000
echo  Press Ctrl+C to stop
echo ==============================
echo.
echo 流程说明：
echo   1. 上传 PDF，选择 PPT 配置（模板/页数/语言/风格/受众）
echo   2. 后台自动生成 PPT（SVG + PPTX + 演讲稿）并建立问答知识库
echo   3. 相同 PDF + 相同配置命中缓存，无需重新生成
echo   4. 生成完成后展示 PPT 并支持论文问答
echo.
echo 依赖：
echo   - Python：使用当前环境中的 python，或预先设置 PYTHON_EXE
echo   - SKILL_DIR：在 .env 中配置 paper-to-ppt skill 路径
echo   - Claude CLI：若不在 PATH 中，请在 .env 中配置 CLAUDE_CLI_PATH
echo   - LLM_API_KEY：在 .env 中配置可用的 API Key
echo.

REM ── 检查前端是否已 build ──
if not exist "..\frontend\dist\index.html" (
    echo [INFO] 前端未构建，正在构建...
    cd ..\frontend
    call npm install
    call npm run build
    cd ..\backend
    echo [INFO] 前端构建完成
    echo.
)

REM ── 检查 .env ──
if not exist ".env" (
    echo [WARN] .env 文件不存在，请复制 .env.example 并填写配置
    copy .env.example .env
    echo [INFO] 已创建 .env，请编辑后重新运行
    pause
    exit /b 1
)

set PYTHONPATH=%~dp0
"%PYTHON_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
