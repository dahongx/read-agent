@echo off
title Reading Agent Backend
cd /d "%~dp0"
set PYTHONPATH=%~dp0
if not defined PYTHON_EXE set "PYTHON_EXE=python"

echo ==============================
echo  Starting backend on :8000
echo  Docs: http://localhost:8000/docs
echo  Press Ctrl+C to stop
echo ==============================
echo.

"%PYTHON_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Server stopped. Press any key to close.
pause