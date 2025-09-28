import os, requests
from dotenv import load_dotenv

load_dotenv()

DUFFEL_BASE = "https://api.duffel.com/air"

def test_flights():
    token = os.getenv("DUFFEL_ACCESS_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Duffel-Version": "v1",
        "Content-Type": "application/json"
    }

    body = {
        "data": {
            "slices": [
                {"origin": "CMB", "destination": "TYO", "departure_date": "2025-10-01"},
                {"origin": "TYO", "destination": "CMB", "departure_date": "2025-10-08"}
            ],
            "passengers": [{"type": "adult"}],
            "max_connections": 1
        }
    }

    r = requests.post(f"{DUFFEL_BASE}/offer_requests", headers=headers, json=body)
    print("Flights:", r.status_code, r.json())

if __name__ == "__main__":
    test_flights()
