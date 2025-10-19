import requests
import json

# Test the enhanced API
print("Testing Enhanced API...")

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
    "themes": ["beach", "culture"]
}

try:
    print("Sending enhanced request...")
    response = requests.post(
        "http://localhost:8000/api/generate-itinerary",
        json=test_data,
        timeout=120  # 2 minutes timeout
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS! Enhanced itinerary generated")
        
        # Check if we have the expected data structure
        if "plans" in result:
            plan = result["plans"][0]
            print(f"Plan title: {plan.get('title', 'No title')}")
            
            if "daily_plan" in plan:
                print(f"Number of days: {len(plan['daily_plan'])}")
                
                for i, day in enumerate(plan["daily_plan"]):
                    print(f"\nDay {i+1}: {day.get('title', 'No title')}")
                    print(f"  Location: {day.get('base_city', 'Unknown')}")
                    print(f"  Weather: {day.get('weather_hint', 'Unknown')}")
                    
                    if "activities" in day and day["activities"]:
                        print(f"  Activities ({len(day['activities'])}):")
                        for j, activity in enumerate(day["activities"]):
                            if activity:  # Check if activity is not None
                                print(f"    {j+1}. {activity.get('name', 'Unknown')}")
                                print(f"       Type: {activity.get('kind', 'Unknown')}")
                                print(f"       Time: {activity.get('start_time', 'Unknown')}")
                                print(f"       Duration: {activity.get('duration_minutes', 0)} min")
                                
                                # Check for enhanced data
                                if "weather_info" in activity and activity["weather_info"]:
                                    weather = activity["weather_info"]
                                    print(f"       Weather: {weather.get('condition', 'Unknown')} - {weather.get('temperature', 'N/A')}°C")
                                
                                if "nearby_restaurants" in activity and activity["nearby_restaurants"]:
                                    restaurants = activity["nearby_restaurants"]
                                    print(f"       Restaurants: {len(restaurants)} nearby")
                                
                                if "image_url" in activity:
                                    print(f"       Image: {activity['image_url'][:50]}...")
                            else:
                                print(f"    {j+1}. [Empty activity]")
                    
                    if "travel_legs" in day:
                        print(f"  Transport ({len(day['travel_legs'])}):")
                        for j, leg in enumerate(day["travel_legs"]):
                            from_place = leg.get('from', leg.get('from_', 'Unknown'))
                            to_place = leg.get('to', 'Unknown')
                            distance = leg.get('km', leg.get('distance_km', 0))
                            duration = leg.get('eta_min', leg.get('duration_minutes', 0))
                            cost = leg.get('estimated_cost', 0)
                            currency = leg.get('cost_currency', 'USD')
                            
                            print(f"    {j+1}. {from_place} → {to_place}")
                            print(f"       Distance: {distance} km")
                            print(f"       Duration: {duration} min")
                            print(f"       Cost: {currency} {cost}")
                            print(f"       Raw leg data: {leg}")
            else:
                print("No daily_plan found in result")
        else:
            print("No plans found in result")
            
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Connection Error: {e}")
