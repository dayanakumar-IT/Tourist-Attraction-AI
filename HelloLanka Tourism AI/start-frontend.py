#!/usr/bin/env python3
"""
Frontend startup script for HelloLanka Tourism AI
"""

import subprocess
import os
from pathlib import Path

def main():
    # Change to frontend directory
    frontend_dir = Path(__file__).parent / "sri-lanka-ai-planner"
    os.chdir(frontend_dir)
    
    print("🎨 Starting Frontend Development Server...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    try:
        subprocess.run(["npm", "start"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Frontend server stopped")
    except Exception as e:
        print(f"❌ Frontend error: {e}")

if __name__ == "__main__":
    main()
