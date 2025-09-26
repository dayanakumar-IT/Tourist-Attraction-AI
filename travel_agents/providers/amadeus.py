import os
import httpx
from typing import List, Optional, Tuple
from datetime import date, timedelta

AMADEUS_BASE = "https://test.api.amadeus.com"
CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

async def _get_token() -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{AMADEUS_BASE}/v1/security/oauth2/token",
            data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        return r.json()["access_token"]
    
async def find_city_code(destination: str) -> Optional[str]:
        """Resolve common Sri Lankan destinations to city codes quickly.
        Falls back to Amadeus locations API if needed.
        """
        mapping = {
        "sri lanka": "CMB", # default to Colombo
        "colombo": "CMB",
        "kandy": "KDZ",
        "galle": "KCT",
        "jaffna": "JAF",
        }
        key = destination.strip().lower()
        if key in mapping:
            return mapping[key]
        token = await _get_token()
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
            f"{AMADEUS_BASE}/v1/reference-data/locations",
            params={"keyword": destination, "subType": "CITY,AIRPORT"},
            headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            for item in data:
                if item.get("subType") == "CITY":
                    return item.get("iataCode")
            if data:
                return data[0].get("iataCode")
        return None


async def search_flights_amadeus(origin_iata: str, dest_iata: str, depart_date: str, return_date: Optional[str], adults: int = 1):
    token = await _get_token()
    params = {
        "originLocationCode": origin_iata,
        "destinationLocationCode": dest_iata,
        "departureDate": depart_date,
        "adults": str(adults),
        "currencyCode": "USD",
        "max": "10",
    }
    if return_date:
        params["returnDate"] = return_date
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{AMADEUS_BASE}/v2/shopping/flight-offers",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()
        
async def search_hotels_amadeus(city_code: str, check_in: str, check_out: str, adults: int = 1):
    token = await _get_token()
    params = {
    "cityCode": city_code,
    "adults": str(adults),
    "checkInDate": check_in,
    "checkOutDate": check_out,
    "roomQuantity": "1",
    "paymentPolicy": "NONE",
    "bestRateOnly": "true",
    "currency": "LKR",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{AMADEUS_BASE}/v3/shopping/hotel-offers",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()