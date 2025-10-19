import sys
import os
sys.path.append('src')
from agents.transport_agent import TransportAgent
import json

# Test the transport optimization directly
print("Testing transport optimization directly...")

# Sample itinerary data (similar to what the API returns)
sample_data = {
    "title": "Test Itinerary",
    "daily_plan": [
        {
            "date": "2025-12-20",
            "base_city": "Galle",
            "activities": [
                {
                    "name": "Test Activity",
                    "kind": "beach",
                    "start": "08:30:00",
                    "duration_min": 90
                }
            ],
            "travel_legs": [
                {
                    "mode": "car",
                    "from": "Colombo",
                    "to": "Galle",
                    "eta_min": 144,
                    "km": 108.3,
                    "estimated_cost": None,
                    "cost_currency": None
                }
            ]
        }
    ]
}

try:
    transport_agent = TransportAgent()
    result = transport_agent.optimize_itinerary_transport(sample_data, group_size=2, budget_currency="LKR")
    
    print("=== TRANSPORT OPTIMIZATION RESULT ===")
    print(json.dumps(result, indent=2))
    
    # Check if cost was added
    for day in result.get("daily_plan", []):
        for leg in day.get("travel_legs", []):
            cost = leg.get("estimated_cost")
            currency = leg.get("cost_currency")
            print(f"Leg: {leg.get('from')} → {leg.get('to')}")
            print(f"  Cost: {currency} {cost}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
