#!/usr/bin/env python3
"""
Test to verify real places are being used instead of placeholders.
"""

import requests
import json

def test_real_places():
    """Test that real places are returned instead of placeholders."""
    
    # Test with wildlife theme
    print("🦁 Testing Wildlife Theme...")
    wildlife_data = {
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
        response = requests.post("http://localhost:8000/api/generate-itinerary", json=wildlife_data)
        if response.status_code == 200:
            result = response.json()
            plan = result.get("plan", {})
            print(f"✅ Wildlife Plan: {plan.get('title', 'No title')}")
            
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
                    elif any(real_place in name.lower() for real_place in ["yala", "udawalawe", "minneriya", "sinharaja", "wilpattu", "elephant", "safari", "national park"]):
                        real_places_found.append(name)
            
            print(f"🦁 Real places found: {real_places_found}")
            print(f"⚠️ Placeholders found: {placeholder_found}")
            
            if real_places_found:
                print("✅ SUCCESS: Real places are being used!")
            else:
                print("❌ ISSUE: No real places found, only placeholders")
                
        else:
            print(f"❌ Wildlife test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Wildlife test error: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Test with beach theme
    print("🏖️ Testing Beach Theme...")
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
                    elif any(real_place in name.lower() for real_place in ["unawatuna", "mirissa", "bentota", "arugam", "hikkaduwa", "beach"]):
                        real_places_found.append(name)
            
            print(f"🏖️ Real places found: {real_places_found}")
            print(f"⚠️ Placeholders found: {placeholder_found}")
            
            if real_places_found:
                print("✅ SUCCESS: Real places are being used!")
            else:
                print("❌ ISSUE: No real places found, only placeholders")
                
        else:
            print(f"❌ Beach test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Beach test error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Real Places Integration")
    print("=" * 60)
    test_real_places()
    print("\n🎉 Real places testing complete!")
