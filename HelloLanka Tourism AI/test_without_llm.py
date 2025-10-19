import sys
import os
sys.path.append('src')
from agents.planner_agent import PlannerAgent
from agents.weather_food_agent import WeatherFoodAgent
from agents.transport_agent import TransportAgent
from contracts import TripNormalized
import json

# Test the agents directly without LLM
print("Testing agents directly without LLM...")

# Create a sample trip request
trip_data = {
    "start_location": "Colombo",
    "destinations": ["Galle"],
    "start_date": "2025-12-20",
    "trip_days": 2,
    "budget": {
        "amount": 1000,
        "currency": "USD"
    },
    "party": {
        "type": "couple",
        "count": 2,
        "notes": ""
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
    # 1. Normalize the request
    print("1. Normalizing request...")
    normalized = TripNormalized(
        start_location=trip_data["start_location"],
        destinations=trip_data["destinations"],
        start_date=trip_data["start_date"],
        trip_days=trip_data["trip_days"],
        budget=trip_data["budget"],
        party=trip_data["party"],
        accommodation=trip_data["accommodation"],
        experiences=trip_data["experiences"],
        themes=trip_data["themes"],
        traveler_profile=trip_data["traveler_profile"]
    )
    print(f"   ✅ Normalized: {normalized.start_location} → {normalized.destinations}")
    
    # 2. Plan the itinerary
    print("2. Planning itinerary...")
    planner = PlannerAgent()
    plans = planner.plan(normalized)
    print(f"   ✅ Generated {len(plans)} plans")
    
    # 3. Enhance with weather and food
    print("3. Adding weather and food data...")
    weather_food_agent = WeatherFoodAgent()
    enhanced_plan = weather_food_agent.enhance_itinerary(plans[0].model_dump(by_alias=True, mode="json"))
    print(f"   ✅ Enhanced with weather and food data")
    
    # 4. Optimize transport
    print("4. Optimizing transport...")
    transport_agent = TransportAgent()
    final_plan = transport_agent.optimize_itinerary_transport(enhanced_plan, group_size=2, budget_currency="LKR")
    print(f"   ✅ Optimized transport with cost data")
    
    # 5. Display results
    print("\n" + "="*50)
    print("🎉 FINAL ITINERARY (No LLM Required)")
    print("="*50)
    
    plan = final_plan
    print(f"Title: {plan.get('title', 'No title')}")
    print(f"Themes: {plan.get('theme_mix', [])}")
    
    for i, day in enumerate(plan.get("daily_plan", [])):
        print(f"\n📅 Day {i+1}: {day.get('base_city', 'Unknown')}")
        print(f"   Weather: {day.get('weather_hint', 'Unknown')}")
        
        # Activities
        activities = day.get("activities", [])
        print(f"   🎯 Activities ({len(activities)}):")
        for j, activity in enumerate(activities):
            print(f"      {j+1}. {activity.get('name', 'Unknown')}")
            print(f"         Type: {activity.get('kind', 'Unknown')}")
            print(f"         Time: {activity.get('start', 'Unknown')}")
            print(f"         Duration: {activity.get('duration_min', 0)} min")
            
            # Weather info
            if activity.get('weather_info'):
                weather = activity['weather_info']
                print(f"         Weather: {weather.get('condition', 'Unknown')} - {weather.get('temperature', 'N/A')}°C")
            
            # Restaurants
            if activity.get('nearby_restaurants'):
                restaurants = activity['nearby_restaurants']
                print(f"         Restaurants: {len(restaurants)} nearby")
            
            # Image
            if activity.get('image_url'):
                print(f"         Image: {activity['image_url'][:50]}...")
        
        # Transport
        travel_legs = day.get("travel_legs", [])
        if travel_legs:
            print(f"   🚗 Transport ({len(travel_legs)}):")
            for j, leg in enumerate(travel_legs):
                from_place = leg.get('from', 'Unknown')
                to_place = leg.get('to', 'Unknown')
                distance = leg.get('km', 0)
                duration = leg.get('eta_min', 0)
                cost = leg.get('estimated_cost', 0)
                currency = leg.get('cost_currency', 'LKR')
                
                print(f"      {j+1}. {from_place} → {to_place}")
                print(f"         Distance: {distance} km")
                print(f"         Duration: {duration} min")
                print(f"         Cost: {currency} {cost}")
        else:
            print(f"   🚗 Transport: No travel legs")
    
    print("\n" + "="*50)
    print("✅ SUCCESS! All agents working without LLM!")
    print("="*50)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
