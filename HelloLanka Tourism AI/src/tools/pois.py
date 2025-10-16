# src/tools/pois.py
import requests, re
from typing import List, Dict, Any
from ..settings import OPENTRIPMAP_API_KEY, HTTP_TIMEOUT

BASE = "https://api.opentripmap.com/0.1/en/places/radius"

def _raise_if_bad(r: requests.Response):
    if not r.ok:
        # include body so you can see OTM’s actual complaint
        raise RuntimeError(f"OpenTripMap error {r.status_code}: {r.text}")

def search_radius(lat: float, lon: float, kinds: List[str], radius=6000, limit=6) -> List[Dict[str,Any]]:
    """Strict kinds-based search. Raises if key missing or OTM rejects params."""
    if not OPENTRIPMAP_API_KEY:
        raise RuntimeError("Missing OPENTRIPMAP_API_KEY in .env")
    if not kinds:
        raise ValueError("kinds list is empty; use search_radius_general_filtered for name-based filtering")

    kinds_str = ",".join(kinds)
    r = requests.get(
        BASE,
        params={
            "apikey": OPENTRIPMAP_API_KEY,
            "radius": radius,
            "lon": lon,
            "lat": lat,
            "kinds": kinds_str,
            "limit": limit,
            "rate": 2,
            "format": "json",
        },
        timeout=HTTP_TIMEOUT,
    )
    _raise_if_bad(r)
    data = r.json()
    if not isinstance(data, list) or not data:
        raise ValueError(f"No POIs returned for {lat},{lon} kinds={kinds_str}")
    return data

def search_radius_general_filtered(
    lat: float, lon: float, include_name_regex: str, radius=6000, limit=20
) -> List[Dict[str,Any]]:
    """Query without kinds, then filter by name regex (still live data)."""
    if not OPENTRIPMAP_API_KEY:
        raise RuntimeError("Missing OPENTRIPMAP_API_KEY in .env")
    r = requests.get(
        BASE,
        params={
            "apikey": OPENTRIPMAP_API_KEY,
            "radius": radius,
            "lon": lon,
            "lat": lat,
            "limit": limit,
            "rate": 2,
            "format": "json",
        },
        timeout=HTTP_TIMEOUT,
    )
    _raise_if_bad(r)
    data = r.json()
    if not isinstance(data, list) or not data:
        raise ValueError(f"No POIs returned for {lat},{lon} (no kinds)")

    pat = re.compile(include_name_regex, re.IGNORECASE)
    filtered = [p for p in data if pat.search(p.get("name",""))]
    if not filtered:
        raise ValueError(f"No POIs matched name filter /{include_name_regex}/ near {lat},{lon}")
    return filtered

def search_radius_name_filtered_multi(
    lat: float,
    lon: float,
    include_name_regex: str,
    radii: list[int] = [6000, 10000, 15000],
    per_radius_limit: int = 40,
) -> List[Dict[str, Any]]:
    """Try multiple radii, return first non-empty set of POIs whose name matches regex."""
    if not OPENTRIPMAP_API_KEY:
        raise RuntimeError("Missing OPENTRIPMAP_API_KEY in .env")

    pat = re.compile(include_name_regex, re.IGNORECASE)

    for r_km in radii:
        r = requests.get(
            BASE,
            params={
                "apikey": OPENTRIPMAP_API_KEY,
                "radius": r_km,
                "lon": lon,
                "lat": lat,
                "limit": per_radius_limit,
                "rate": 2,
                "format": "json",
            },
            timeout=HTTP_TIMEOUT,
        )
        _raise_if_bad(r)
        data = r.json()
        if not isinstance(data, list) or not data:
            continue
        filtered = [p for p in data if pat.search(p.get("name", ""))]
        if filtered:
            return filtered
    return []

def diag_test_opentripmap(lat: float, lon: float):
    """Minimal probe used by orchestrator --diag."""
    if not OPENTRIPMAP_API_KEY:
        raise RuntimeError("Missing OPENTRIPMAP_API_KEY in .env")
    r = requests.get(
        BASE,
        params={
            "apikey": OPENTRIPMAP_API_KEY,
            "radius": 500,
            "lon": lon,
            "lat": lat,
            "limit": 1,
            "format": "json",
        },
        timeout=HTTP_TIMEOUT,
    )
    _raise_if_bad(r)
    if not r.json():
        raise RuntimeError("OpenTripMap returned empty list on probe")
