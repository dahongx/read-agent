@echo off
setlocal EnableExtensions
title Reading Agent Backend
cd /d "%~dp0"

if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        set "%%A=%%B"
    )
)

set "PYTHONPATH=%~dp0"

if not defined PYTHON_EXE (
    if exist "D:\program\anaconda3\envs\pocket-souls\python.exe" (
        set "PYTHON_EXE=D:\program\anaconda3\envs\pocket-souls\python.exe"
    ) else (
        set "PYTHON_EXE=python"
    )
)

if not exist ".env" (
    echo .env file not found. Copy .env.example to .env and fill in the settings.
    pause
    exit /b 1
)

if not exist "..\frontend\dist\index.html" (
    echo Frontend build not found. Building frontend...
    pushd ..\frontend
    call npm install
    if errorlevel 1 goto :fail
    call npm run build
    if errorlevel 1 goto :fail
    popd
    echo Frontend build complete.
    echo.
)

echo Starting backend at http://localhost:8000
echo Open http://localhost:8000/docs for API docs
echo.

"%PYTHON_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8000

goto :done

:fail
echo.
echo Startup failed.
pause
exit /b 1

:done
pause
