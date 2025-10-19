import sys
import os
sys.path.append('src')
from agents.planner_agent import PlannerAgent
from agents.weather_food_agent import WeatherFoodAgent
from agents.transport_agent import TransportAgent
from contracts import TripNormalized
import json

# Test the agents directly without LLM
print("🚀 Testing Enhanced Multi-Agent System...")
print("="*60)

# Create a comprehensive trip request
trip_data = {
    "start_location": "Colombo",
    "destinations": ["Galle", "Ella"],
    "start_date": "2025-12-20",
    "trip_days": 3,
    "budget": {
        "amount": 1500,
        "currency": "USD"
    },
    "party": {
        "type": "couple",
        "count": 2,
        "notes": "Romantic getaway"
    },
    "accommodation": {
        "needed": True,
        "types": ["hotel", "resort"]
    },
    "experiences": ["beach", "culture", "adventure", "nature"],
    "themes": ["beach", "culture", "adventure", "nature"],
    "traveler_profile": "foreign_tourist"
}

try:
    # 1. Normalize the request
    print("1️⃣ Normalizing request...")
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
    print(f"   📅 Trip Duration: {normalized.trip_days} days")
    print(f"   💰 Budget: {normalized.budget.amount} {normalized.budget.currency}")
    print(f"   👥 Group: {normalized.party.type} ({normalized.party.count} people)")
    
    # 2. Plan the itinerary
    print("\n2️⃣ Planning itinerary with intelligent place suggestions...")
    planner = PlannerAgent()
    plans = planner.plan(normalized)
    print(f"   ✅ Generated {len(plans)} comprehensive plans")
    
    # 3. Enhance with weather and food
    print("\n3️⃣ Adding weather forecasts and food recommendations...")
    weather_food_agent = WeatherFoodAgent()
    enhanced_plan = weather_food_agent.enhance_itinerary(plans[0].model_dump(by_alias=True, mode="json"))
    print(f"   ✅ Enhanced with weather and food data")
    
    # 4. Optimize transport
    print("\n4️⃣ Optimizing transportation routes and costs...")
    transport_agent = TransportAgent()
    final_plan = transport_agent.optimize_itinerary_transport(enhanced_plan, group_size=2, budget_currency="LKR")
    print(f"   ✅ Optimized transport with detailed cost analysis")
    
    # 5. Display comprehensive results
    print("\n" + "="*80)
    print("🎉 COMPREHENSIVE SRI LANKA ITINERARY")
    print("="*80)
    
    plan = final_plan
    print(f"📋 Title: {plan.get('title', 'No title')}")
    print(f"🎯 Themes: {', '.join(plan.get('theme_mix', []))}")
    print(f"📍 Destinations: {' → '.join(plan.get('destinations', []))}")
    
    total_cost = 0
    total_distance = 0
    
    for i, day in enumerate(plan.get("daily_plan", [])):
        print(f"\n📅 Day {i+1}: {day.get('base_city', 'Unknown')}")
        print(f"   🌤️  Weather: {day.get('weather_hint', 'Unknown')}")
        
        # Activities
        activities = day.get("activities", [])
        print(f"   🎯 Activities ({len(activities)}):")
        for j, activity in enumerate(activities):
            print(f"      {j+1}. {activity.get('name', 'Unknown')}")
            print(f"         🏷️  Type: {activity.get('kind', 'Unknown')}")
            print(f"         ⏰ Time: {activity.get('start', 'Unknown')}")
            print(f"         ⏱️  Duration: {activity.get('duration_min', 0)} min")
            
            # Weather info
            if activity.get('weather_info'):
                weather = activity['weather_info']
                print(f"         🌡️  Weather: {weather.get('condition', 'Unknown')} - {weather.get('temperature', 'N/A')}°C")
                print(f"         💡 Tip: {weather.get('tip', 'Enjoy your visit!')}")
            
            # Restaurants
            if activity.get('nearby_restaurants'):
                restaurants = activity['nearby_restaurants']
                print(f"         🍽️  Restaurants: {len(restaurants)} nearby options")
                for k, rest in enumerate(restaurants[:2]):  # Show first 2
                    print(f"            • {rest.get('name', 'Restaurant')} - {rest.get('cuisine', 'Local')}")
            
            # Image
            if activity.get('image_url'):
                print(f"         📸 Image: {activity['image_url'][:50]}...")
        
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
                mode = leg.get('mode', 'driving')
                
                print(f"      {j+1}. {from_place} → {to_place}")
                print(f"         🚙 Mode: {mode.title()}")
                print(f"         📏 Distance: {distance} km")
                print(f"         ⏱️  Duration: {duration} min")
                print(f"         💰 Cost: {currency} {cost}")
                
                total_cost += cost
                total_distance += distance
        else:
            print(f"   🚗 Transport: No travel legs")
    
    print(f"\n📊 TRIP SUMMARY:")
    print(f"   💰 Total Transport Cost: LKR {total_cost}")
    print(f"   📏 Total Distance: {total_distance} km")
    print(f"   🎯 Total Activities: {sum(len(day.get('activities', [])) for day in plan.get('daily_plan', []))}")
    
    print("\n" + "="*80)
    print("✅ SUCCESS! All agents working intelligently!")
    print("🎯 Smart place suggestions, weather forecasts, food recommendations,")
    print("🚗 optimized transport routes, and cost analysis - all working!")
    print("="*80)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
