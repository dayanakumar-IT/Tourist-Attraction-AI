from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from contracts import TripRequest
from agent_graph import run_multiagent

app = FastAPI(title="HelloLanka Tourism AI", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "HelloLanka Tourism AI"}

@app.post("/api/plan")
async def plan_trip(req: TripRequest):
    try:
        result = run_multiagent(req.model_dump(), trace=False)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/generate-itinerary")
async def generate_itinerary(trip_data: dict):
    try:
        # Convert frontend data to TripRequest format
        trip_request = TripRequest(
            start_city=trip_data.get("start_city", "Colombo"),
            destinations=trip_data.get("destinations", []),
            start_date=trip_data.get("start_date", "2025-01-01"),
            trip_days=trip_data.get("trip_days", 5),
            budget=trip_data.get("budget", {"amount": 1000, "currency": "USD"}),
            traveler_profile=trip_data.get("traveler_profile", {}),
            themes=trip_data.get("themes", ["culture", "nature"])
        )
        
        result = run_multiagent(trip_request.model_dump(), trace=False)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


