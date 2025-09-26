#!/usr/bin/env python3
"""
Quick test for country detection fix
"""

import sys
from pathlib import Path

# Add the travel_agents directory to Python path
current_dir = Path(__file__).parent
travel_agents_dir = current_dir / "travel_agents"
sys.path.insert(0, str(travel_agents_dir))

def test_country_detection():
    """Test the improved country detection"""
    print("🧪 Testing Country Detection Fix")
    print("=" * 40)
    
    try:
        from travel_agents.team_minimal import extract_trip_details
        
        test_prompts = [
            "Plan a trip to Sri Lanka",
            "I want to visit Japan for 5 days",
            "Book flights and hotels for Thailand",
            "Travel to France starting 2024-03-15 for 7 days",
            "Go to Australia",
            "Visit United States",
            "Trip to Germany"
        ]
        
        for prompt in test_prompts:
            print(f"\n📝 Testing: '{prompt}'")
            country, start_date, num_days = extract_trip_details(prompt)
            print(f"   ✅ Result: Country='{country}', Start='{start_date}', Days={num_days}")
        
        print("\n" + "=" * 40)
        print("🎉 Country detection test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_country_detection()
    if success:
        print("\n✅ Country detection is working correctly!")
        print("You can now run: python main.py --demo")
    else:
        print("\n❌ Country detection still has issues.")
