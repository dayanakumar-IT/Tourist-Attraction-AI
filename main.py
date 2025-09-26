#!/usr/bin/env python3
"""
Tourist Attraction AI - Main Entry Point
A comprehensive travel planning assistant that finds flights and hotels based on natural language prompts.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the travel_agents directory to Python path
current_dir = Path(__file__).parent
travel_agents_dir = current_dir / "travel_agents"
sys.path.insert(0, str(travel_agents_dir))

def check_environment():
    """Check if required environment variables are set"""
    print("🔧 Checking environment setup...")
    
    # Check if .env file exists
    env_file = travel_agents_dir / ".env"
    if not env_file.exists():
        print("⚠️  No .env file found!")
        print("📝 Please create a .env file with your API keys.")
        print("   You can use env_example.txt as a template.")
        print()
        
        # Show example content
        example_file = travel_agents_dir / "env_example.txt"
        if example_file.exists():
            print("📋 Example .env content:")
            with open(example_file, 'r') as f:
                print(f.read())
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    # Check required keys
    required_keys = [
        "GEMINI_API_KEY",
        "GEOCODE_API_KEY", 
        "AMADEUS_CLIENT_ID",
        "AMADEUS_CLIENT_SECRET"
    ]
    
    missing_keys = []
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        print(f"⚠️  Missing API keys: {', '.join(missing_keys)}")
        print("   Some features may not work properly.")
        print("   Please update your .env file with valid API keys.")
        print()
        return False
    
    print("✅ Environment setup complete!")
    return True

def show_help():
    """Show help information"""
    print("""
🌍 Tourist Attraction AI - Help
===============================

This application helps you plan trips by finding flights and hotels based on natural language prompts.

USAGE:
    python main.py [options]

OPTIONS:
    --help, -h          Show this help message
    --check-env         Check environment setup only
    --demo              Run in demo mode (no API calls)

EXAMPLES:
    python main.py
    python main.py --demo
    python main.py --check-env

FEATURES:
    ✈️  Flight search via Amadeus and Duffel APIs
    🏨 Hotel search via Amadeus API
    🤖 AI-powered trip planning with Gemini
    🌍 Automatic country detection from prompts
    📅 Flexible date handling
    💰 Price comparison and package creation

REQUIRED API KEYS:
    • GEMINI_API_KEY - For AI planning features
    • GEOCODE_API_KEY - For location detection
    • AMADEUS_CLIENT_ID - For flight/hotel search
    • AMADEUS_CLIENT_SECRET - For flight/hotel search
    • DUFFEL_ACCESS_TOKEN - For additional flight options (optional)

For more information, visit: https://github.com/your-repo/tourist-attraction-ai
""")

async def run_demo_mode():
    """Run the application in demo mode with mock data"""
    print("🎭 Running in DEMO MODE")
    print("=" * 30)
    print("This mode uses mock data and doesn't require API keys.")
    print()
    
    # Import and run the main function
    try:
        from travel_agents.team_minimal import main
        await main()
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        return False
    
    return True

async def run_normal_mode():
    """Run the application in normal mode"""
    print("🚀 Starting Tourist Attraction AI...")
    print("=" * 40)
    
    # Check environment first
    if not check_environment():
        print("❌ Environment setup incomplete. Please fix the issues above.")
        return False
    
    # Import and run the main function
    try:
        from travel_agents.team_minimal import main
        await main()
    except Exception as e:
        print(f"❌ Error running application: {e}")
        print("💡 Try running with --demo flag for testing without API keys")
        return False
    
    return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Tourist Attraction AI - Your Personal Travel Assistant",
        add_help=False
    )
    parser.add_argument('--help', '-h', action='store_true', help='Show help message')
    parser.add_argument('--check-env', action='store_true', help='Check environment setup only')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode')
    
    args = parser.parse_args()
    
    if args.help:
        show_help()
        return
    
    if args.check_env:
        check_environment()
        return
    
    # Run the appropriate mode
    try:
        if args.demo:
            success = asyncio.run(run_demo_mode())
        else:
            success = asyncio.run(run_normal_mode())
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Thanks for using Tourist Attraction AI!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("💡 Try running with --help for more information")
        sys.exit(1)

if __name__ == "__main__":
    main()
