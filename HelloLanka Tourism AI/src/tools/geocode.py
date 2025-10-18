# src/tools/geocode.py
import requests
from typing import Dict
from settings import USER_AGENT, HTTP_TIMEOUT

def geocode_nominatim(query: str) -> Dict[str, float]:
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f"No coordinates found for '{query}'")
    hit = data[0]
    return {"lat": float(hit["lat"]), "lon": float(hit["lon"])}
