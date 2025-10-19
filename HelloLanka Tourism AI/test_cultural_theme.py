#!/usr/bin/env python3
"""
Test cultural theme to verify real places are working.
"""

import requests
import json

def test_cultural_theme():
    """Test cultural theme with real places."""
    
    print("🏛️ Testing Cultural Theme...")
    cultural_data = {
        "start_location": "Colombo",
        "destinations": ["Kandy"],
        "start_date": "2025-01-20",
        "trip_days": 2,
        "budget": {"amount": 2000, "currency": "USD"},
        "party": {"type": "couple", "count": 2, "notes": ""},
        "accommodation": {"needed": True, "types": ["hotel"]},
        "experiences": ["culture"],
        "themes": ["culture"],
        "traveler_profile": "foreign_tourist",
        "chat_interests": ["culture"],
        "free_text_interest": "I want to see ancient temples and cultural sites"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/generate-itinerary", json=cultural_data)
        if response.status_code == 200:
            result = response.json()
            plan = result.get("plan", {})
            print(f"✅ Cultural Plan: {plan.get('title', 'No title')}")
            
            # Check for real places
            daily_plans = plan.get("daily_plan", [])
            real_places_found = []
            placeholder_found = []
            
            for day in daily_plans:
                activities = day.get("activities", [])
                for activity in activities:
                    name = activity.get("name", "")
                    if "placeholder" in name.lower():
                        placeholder_found.append(name)
                    elif any(real_place in name.lower() for real_place in ["temple", "sigiriya", "dambulla", "galle fort", "anuradhapura", "tooth relic", "sacred"]):
                        real_places_found.append(name)
            
            print(f"🏛️ Real places found: {real_places_found}")
            print(f"⚠️ Placeholders found: {placeholder_found}")
            
            if real_places_found:
                print("✅ SUCCESS: Real cultural places are being used!")
            else:
                print("❌ ISSUE: No real cultural places found")
                
        else:
            print(f"❌ Cultural test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cultural test error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Cultural Theme with Real Places")
    print("=" * 60)
    test_cultural_theme()
    print("\n🎉 Cultural theme testing complete!")
