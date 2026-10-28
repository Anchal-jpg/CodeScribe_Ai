Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting CodeScribe AI Backend (CodeT5-50K)..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

& "$scriptDir\backend\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
