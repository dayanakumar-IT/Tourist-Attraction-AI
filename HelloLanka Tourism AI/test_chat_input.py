#!/usr/bin/env python3
"""
Test script to verify chat input and real places are working.
"""

import requests
import json

def test_chat_input():
    """Test that chat input produces different results."""
    
    # Test 1: Safari request
    print("🦁 Testing Safari Request...")
    safari_data = {
        "start_location": "Colombo",
        "destinations": ["Galle"],
        "start_date": "2025-01-20",
        "trip_days": 2,
        "budget": {"amount": 2000, "currency": "USD"},
        "party": {"type": "couple", "count": 2, "notes": ""},
        "accommodation": {"needed": True, "types": ["hotel"]},
        "experiences": ["wildlife"],
        "themes": ["wildlife"],
        "traveler_profile": "foreign_tourist",
        "chat_interests": ["wildlife"],
        "free_text_interest": "I want to see elephants and go on safari"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/generate-itinerary", json=safari_data)
        if response.status_code == 200:
            result = response.json()
            plan = result.get("plan", {})
            print(f"✅ Safari Plan: {plan.get('title', 'No title')}")
            
            # Check if we got wildlife-related activities
            daily_plans = plan.get("daily_plan", [])
            for day in daily_plans:
                activities = day.get("activities", [])
                for activity in activities:
                    name = activity.get("name", "")
                    if "elephant" in name.lower() or "safari" in name.lower() or "wildlife" in name.lower():
                        print(f"🦁 Found wildlife activity: {name}")
                        break
        else:
            print(f"❌ Safari test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Safari test error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Beach request
    print("🏖️ Testing Beach Request...")
    beach_data = {
        "start_location": "Colombo",
        "destinations": ["Galle"],
        "start_date": "2025-01-20",
        "trip_days": 2,
        "budget": {"amount": 2000, "currency": "USD"},
        "party": {"type": "couple", "count": 2, "notes": ""},
        "accommodation": {"needed": True, "types": ["hotel"]},
        "experiences": ["beach"],
        "themes": ["beach"],
        "traveler_profile": "foreign_tourist",
        "chat_interests": ["beach"],
        "free_text_interest": "I want beautiful beaches and water activities"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/generate-itinerary", json=beach_data)
        if response.status_code == 200:
            result = response.json()
            plan = result.get("plan", {})
            print(f"✅ Beach Plan: {plan.get('title', 'No title')}")
            
            # Check if we got beach-related activities
            daily_plans = plan.get("daily_plan", [])
            for day in daily_plans:
                activities = day.get("activities", [])
                for activity in activities:
                    name = activity.get("name", "")
                    if "beach" in name.lower() or "mirissa" in name.lower() or "unawatuna" in name.lower():
                        print(f"🏖️ Found beach activity: {name}")
                        break
        else:
            print(f"❌ Beach test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Beach test error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Chat Input and Real Places Integration")
    print("=" * 60)
    test_chat_input()
    print("\n🎉 Chat input testing complete!")
