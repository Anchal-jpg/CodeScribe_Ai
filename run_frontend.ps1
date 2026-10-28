Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting CodeScribe AI Frontend (Vite React)..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\frontend"

npm run dev
