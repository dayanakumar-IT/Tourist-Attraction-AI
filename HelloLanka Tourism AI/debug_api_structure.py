import requests
import json

# Test the API and examine the structure
print("Testing API structure...")

test_data = {
    "start_city": "Colombo",
    "destinations": ["Galle"],
    "start_date": "2025-12-20",
    "trip_days": 2,
    "budget": {
        "amount": 1000,
        "currency": "USD"
    },
    "traveler_profile": {
        "group_type": "couple",
        "group_size": 2,
        "has_elderly": False,
        "special_requirements": ""
    },
    "themes": ["beach"]
}

try:
    response = requests.post(
        "http://localhost:8000/api/generate-itinerary",
        json=test_data,
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        print("=== FULL API RESPONSE STRUCTURE ===")
        print(json.dumps(result, indent=2))
        
        # Check if we have plans
        if "plans" in result:
            print(f"\n=== PLANS FOUND: {len(result['plans'])} ===")
            for i, plan in enumerate(result["plans"]):
                print(f"Plan {i+1}: {plan.get('title', 'No title')}")
                if "daily_plan" in plan:
                    print(f"  Daily plans: {len(plan['daily_plan'])}")
                    for j, day in enumerate(plan["daily_plan"]):
                        print(f"    Day {j+1}: {day.get('title', 'No title')}")
                        if "travel_legs" in day:
                            print(f"      Travel legs: {len(day['travel_legs'])}")
                            for k, leg in enumerate(day["travel_legs"]):
                                print(f"        Leg {k+1}: {leg}")
        else:
            print("\n=== NO PLANS FOUND ===")
            print("Available keys:", list(result.keys()))
    else:
        print(f"Error: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
