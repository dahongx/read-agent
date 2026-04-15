@echo off
title Reading Agent Frontend
cd /d "%~dp0"

echo ==============================
echo  Starting frontend on :5173
echo  Open: http://localhost:5173
echo  (Backend must be running on :8000)
echo  Press Ctrl+C to stop
echo ==============================
echo.

npm run dev

echo.
echo Server stopped. Press any key to close.
pause
