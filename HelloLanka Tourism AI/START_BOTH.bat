@echo off
echo 🎉 Starting HelloLanka Tourism AI - Complete System
echo ============================================================
echo.
echo Starting Backend...
start "Backend" cmd /k "cd src && python -m uvicorn simple_server:app --reload --host 0.0.0.0 --port 8000"
echo.
echo Waiting 3 seconds for backend to start...
timeout /t 3 /nobreak >nul
echo.
echo Starting Frontend...
start "Frontend" cmd /k "cd sri-lanka-ai-planner && npm start"
echo.
echo ✅ Both servers are starting!
echo 📍 Backend: http://localhost:8000
echo 🎨 Frontend: http://localhost:3000
echo.
pause
