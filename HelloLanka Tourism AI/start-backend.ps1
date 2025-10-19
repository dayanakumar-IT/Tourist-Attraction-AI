Write-Host "🚀 Starting Backend API Server..." -ForegroundColor Green
Set-Location "src"
uvicorn server:app --reload --port 8000 --host 0.0.0.0
