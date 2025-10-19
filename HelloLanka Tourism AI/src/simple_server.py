from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
sys.path.append('src')
from agents.planner_agent import PlannerAgent
from agents.weather_food_agent import WeatherFoodAgent
from agents.transport_agent import TransportAgent
from contracts import TripNormalized
import json

app = FastAPI(title="HelloLanka Tourism AI", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "HelloLanka Tourism AI is running!"}

@app.post("/api/generate-itinerary")
async def generate_itinerary(trip_data: dict):
    try:
        print(f"🚀 Generating itinerary for: {trip_data.get('start_location', 'Unknown')}")
        
        # Process chat input and interests
        chat_interests = trip_data.get("chat_interests", [])
        free_text_interest = trip_data.get("free_text_interest", "")
        
        # Combine experiences with chat interests
        base_experiences = trip_data.get("experiences", ["beach", "culture"])
        all_interests = list(set(base_experiences + chat_interests))
        
        # Process free text interest using pre-agent
        if free_text_interest:
            print(f"📝 Processing free text: '{free_text_interest}'")
            try:
                from agents.pre_agent import normalize_themes
                normalized_themes = normalize_themes(all_interests, free_text_interest)
                all_interests = normalized_themes
                print(f"🎯 Normalized themes: {all_interests}")
            except Exception as e:
                print(f"⚠️ Theme normalization failed: {e}, using original interests")
        
        print(f"🎯 Final interests: {all_interests}")
        
        # Convert frontend data to TripNormalized format
        normalized = TripNormalized(
            start_location=trip_data.get("start_location", "Colombo"),
            destinations=trip_data.get("destinations", ["Galle"]),
            start_date=trip_data.get("start_date", "2025-12-20"),
            trip_days=trip_data.get("trip_days", 2),
            budget={
                "amount": trip_data.get("budget", {}).get("amount", 1000),
                "currency": trip_data.get("budget", {}).get("currency", "USD")
            },
            party={
                "type": trip_data.get("party", {}).get("type", "couple"),
                "count": trip_data.get("party", {}).get("count", 2),
                "notes": trip_data.get("party", {}).get("notes", "")
            },
            accommodation={
                "needed": trip_data.get("accommodation", {}).get("needed", True),
                "types": trip_data.get("accommodation", {}).get("types", ["hotel"])
            },
            experiences=all_interests,
            themes=all_interests,
            traveler_profile="foreign_tourist"  # Fixed: use literal value
        )
        
        print(f"✅ Normalized request: {normalized.start_location} → {normalized.destinations}")
        
        # 1. Plan the itinerary
        print("🎯 Planning itinerary...")
        planner = PlannerAgent()
        plans = planner.plan(normalized)
        print(f"✅ Generated {len(plans)} plans")
        
        # 2. Enhance with weather and food
        print("🌤️ Adding weather and food data...")
        weather_food_agent = WeatherFoodAgent()
        enhanced_plan = weather_food_agent.enhance_itinerary(plans[0].model_dump(by_alias=True, mode="json"))
        print("✅ Enhanced with weather and food data")
        
        # 3. Optimize transport
        print("🚗 Optimizing transportation...")
        transport_agent = TransportAgent()
        group_size = normalized.party.count
        budget_currency = "LKR"  # Convert to LKR for cost calculation
        final_plan = transport_agent.optimize_itinerary_transport(
            enhanced_plan, group_size, budget_currency
        )
        print("✅ Optimized transport with cost data")
        
        # 4. Return the result
        result = {
            "plan": final_plan,
            "status": "success",
            "message": "Itinerary generated successfully!"
        }
        
        print(f"🎉 Successfully generated itinerary: {final_plan.get('title', 'No title')}")
        return result
        
    except Exception as e:
        print(f"❌ Error generating itinerary: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating itinerary: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
