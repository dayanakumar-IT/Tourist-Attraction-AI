#!/usr/bin/env python3
"""
Start the simplified backend server for HelloLanka Tourism AI
"""

import os
import sys
import subprocess

def main():
    print("🚀 Starting HelloLanka Tourism AI - Simplified Backend")
    print("=" * 60)
    
    # Change to src directory
    src_dir = os.path.join(os.getcwd(), "src")
    if not os.path.exists(src_dir):
        print("❌ Error: src directory not found!")
        return
    
    print(f"📁 Working directory: {src_dir}")
    os.chdir(src_dir)
    
    try:
        print("🌐 Starting FastAPI server...")
        print("📍 Server will be available at: http://localhost:8000")
        print("📚 API docs at: http://localhost:8000/docs")
        print("🔄 Press Ctrl+C to stop the server")
        print("-" * 60)
        
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "simple_server:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
