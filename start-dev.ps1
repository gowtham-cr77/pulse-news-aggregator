# Launch PULSE Backend (FastAPI) and Frontend (Vite) in parallel terminals
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting PULSE Backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"

Write-Host "Starting PULSE Frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
