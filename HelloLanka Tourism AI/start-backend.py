#!/usr/bin/env python3
"""
Backend startup script for HelloLanka Tourism AI
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    # Change to src directory
    src_dir = Path(__file__).parent / "src"
    os.chdir(src_dir)
    
    print("🚀 Starting Backend API Server...")
    print(f"📁 Working directory: {os.getcwd()}")
    
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

if __name__ == "__main__":
    main()
