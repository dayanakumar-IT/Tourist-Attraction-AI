import os
import httpx
from typing import Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


DUFFEL_TOKEN = os.getenv("DUFFEL_ACCESS_TOKEN")
DUFFEL_BASE = "https://api.duffel.com"


HEADERS = {
    "Authorization": f"Bearer {DUFFEL_TOKEN}" if DUFFEL_TOKEN else "",
    "Duffel-Version": "v1",
    "Content-Type": "application/json",
}

async def search_flights_duffel(origin_iata: str, dest_iata: str, depart_date: str, return_date: Optional[str], adults: int = 1):
    if not DUFFEL_TOKEN:
        return None
    payload = {
        "slices": [
            {"origin": origin_iata, "destination": dest_iata, "departure_date": depart_date}
        ],
        "passengers": [{"type": "adult"} for _ in range(adults)],
        "cabin_class": "economy",
        "max_connections": 2,
    }
    if return_date:
        payload["slices"].append({"origin": dest_iata, "destination": origin_iata, "departure_date": return_date})


    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(f"{DUFFEL_BASE}/air/offer_requests", json=payload, headers=HEADERS)
        r.raise_for_status()
        offer_req = r.json()
        offers_url = offer_req["data"]["offers"]["href"]
        r2 = await client.get(f"{DUFFEL_BASE}{offers_url}", headers=HEADERS)
        r2.raise_for_status()
        return r2.json()