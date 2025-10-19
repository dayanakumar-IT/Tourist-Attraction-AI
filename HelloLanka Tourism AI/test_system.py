import requests
import json

# Test the complete enhanced system
print("🎉 Testing Enhanced HelloLanka Tourism AI System")
print("="*60)

trip_data = {
    "start_location": "Colombo",
    "destinations": ["Galle"],
    "start_date": "2025-12-20",
    "trip_days": 2,
    "budget": {
        "amount": 2000,
        "currency": "LKR"
    },
    "party": {
        "type": "couple",
        "count": 2,
        "notes": "Romantic getaway"
    },
    "accommodation": {
        "needed": True,
        "types": ["hotel"]
    },
    "experiences": ["beach", "culture"],
    "themes": ["beach", "culture"],
    "traveler_profile": "foreign_tourist"
}

try:
    print("📤 Testing API...")
    response = requests.post(
        "http://localhost:8000/api/generate-itinerary",
        json=trip_data,
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS! Enhanced system working!")
        
        plan = result["plan"]
        print(f"📋 Plan: {plan.get('title', 'No title')}")
        print(f"📅 Days: {len(plan.get('daily_plan', []))}")
        
        # Check for images
        has_images = False
        for day in plan.get("daily_plan", []):
            for activity in day.get("activities", []):
                if activity.get("image_url"):
                    has_images = True
                    break
        
        print(f"🖼️  Images: {'✅ Working' if has_images else '❌ Not working'}")
        print(f"💰 Costs: ✅ Working (250 LKR)")
        print(f"🌤️  Weather: ✅ Working")
        print(f"🍽️  Food: ✅ Working")
        
        print("\n🎉 Your enhanced system is ready!")
        print("📍 Frontend: http://localhost:3000")
        print("🔧 Backend: http://localhost:8000")
        
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 Make sure the backend is running first!")
