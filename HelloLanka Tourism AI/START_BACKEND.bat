@echo off
echo 🚀 Starting HelloLanka Tourism AI - Enhanced Backend
echo ============================================================
cd src
python -m uvicorn simple_server:app --reload --host 0.0.0.0 --port 8000
pause
