#!/usr/bin/env python3
"""
Simple API test to see the actual error.
"""

import requests
import json

def test_simple_api():
    """Test the API with a simple request."""
    
    data = {
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
        print("📤 Sending request...")
        response = requests.post("http://localhost:8000/api/generate-itinerary", json=data)
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error Response: {response.text}")
        else:
            result = response.json()
            print(f"✅ Success! Plan: {result.get('plan', {}).get('title', 'No title')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_simple_api()
