# SalikChat - Run Backend
Write-Host "Starting SalikChat Backend (FastAPI)..." -ForegroundColor Cyan
Set-Location $PSScriptRoot\backend
C:/Python312/python.exe -m C:\Python312\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
