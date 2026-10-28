@echo off
title CodeScribe AI - Backend Server
echo ========================================================
echo Starting CodeScribe AI Backend (CodeT5-50K)...
echo ========================================================
cd /d "%~dp0"
backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
