#!/usr/bin/env python3
"""
Startup script for HelloLanka Tourism AI
Runs both backend API server and frontend development server
"""

import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path

def run_backend():
    """Start the FastAPI backend server"""
    print("🚀 Starting Backend API Server...")
    os.chdir("src")
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "server:app", 
            "--reload", 
            "--port", "8000",
            "--host", "0.0.0.0"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Backend server stopped")
    except Exception as e:
        print(f"❌ Backend error: {e}")

def run_frontend():
    """Start the React frontend development server"""
    print("🎨 Starting Frontend Development Server...")
    os.chdir("sri-lanka-ai-planner")
    try:
        subprocess.run([
            "npm", "start"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Frontend server stopped")
    except Exception as e:
        print(f"❌ Frontend error: {e}")

def main():
    """Main function to start both servers"""
    print("🌟 HelloLanka Tourism AI - Multi-Agent Web App")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src").exists() or not Path("sri-lanka-ai-planner").exists():
        print("❌ Please run this script from the project root directory")
        print("   Make sure both 'src' and 'sri-lanka-ai-planner' folders exist")
        sys.exit(1)
    
    # Check if frontend dependencies are installed
    if not Path("sri-lanka-ai-planner/node_modules").exists():
        print("📦 Installing frontend dependencies...")
        os.chdir("sri-lanka-ai-planner")
        subprocess.run(["npm", "install"], check=True)
        os.chdir("..")
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Wait a moment for backend to start
    time.sleep(3)
    
    # Start frontend in the main thread
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        sys.exit(0)

if __name__ == "__main__":
    main()
