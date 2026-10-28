@echo off
title CodeScribe AI - Full Stack Launcher
echo ========================================================
echo Launching CodeScribe AI (Backend + Frontend)...
echo ========================================================
start "CodeScribe AI Backend" cmd /k "cd /d "%~dp0" && backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"
start "CodeScribe AI Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo.
echo Both services have been launched!
echo - Backend API:  http://127.0.0.1:8000
echo - API Docs:     http://127.0.0.1:8000/docs
echo - Frontend UI:  http://localhost:5173
echo.
pause
