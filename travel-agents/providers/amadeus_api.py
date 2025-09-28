# providers/amadeus_api.py
import os
import time
import requests
from typing import List, Dict, Any, Optional
from functools import lru_cache

AMADEUS_BASE = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")

# -----------------------------
# OAuth2 token cache
# -----------------------------
_AMD_TOKEN: Optional[str] = None
_AMD_TOKEN_EXP: float = 0.0  # epoch seconds


def _oauth() -> Dict[str, str]:
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET in environment")
    return {"client_id": client_id, "client_secret": client_secret}


def get_token() -> str:
    """Get (and cache) an OAuth2 token."""
    global _AMD_TOKEN, _AMD_TOKEN_EXP
    now = time.time()
    if _AMD_TOKEN and now < (_AMD_TOKEN_EXP - 60):
        return _AMD_TOKEN

    creds = _oauth()
    r = requests.post(
        f"{AMADEUS_BASE}/v1/security/oauth2/token",
        data={"grant_type": "client_credentials",
              "client_id": creds["client_id"],
              "client_secret": creds["client_secret"]},
        timeout=20,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Amadeus OAuth failed: {r.status_code} {r.text}")

    js = r.json()
    _AMD_TOKEN = js.get("access_token")
    _AMD_TOKEN_EXP = now + float(js.get("expires_in", 0))
    if not _AMD_TOKEN:
        raise RuntimeError("Amadeus OAuth returned no access_token")
    return _AMD_TOKEN


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {get_token()}"}


# -----------------------------
# City / Airport search
# -----------------------------
def city_search(keyword: str) -> Optional[str]:
    """
    Resolve free text to a city (or airport) IATA code using Amadeus.
    Returns an uppercase code (e.g., 'PAR', 'LON', 'TYO') or None.
    """
    kw = (keyword or "").strip()
    if not kw:
        return None
    try:
        r = requests.get(
            f"{AMADEUS_BASE}/v1/reference-data/locations",
            params={"subType": "CITY,AIRPORT", "keyword": kw, "page[limit]": 20},
            headers=_auth_headers(),
            timeout=20,
        )
        if r.status_code >= 400:
            return None
        data = r.json().get("data", [])
        if not data:
            return None

        # Prefer exact IATA code matches
        up = kw.upper()
        for item in data:
            if item.get("iataCode", "").upper() == up:
                return up

        # Prefer CITY over AIRPORT
        for item in data:
            if item.get("type") == "location" and item.get("subType") == "CITY":
                code = item.get("iataCode")
                if code:
                    return code.upper()

        # Fallback to first item
        code = data[0].get("iataCode")
        return code.upper() if code else None
    except Exception:
        return None


# -----------------------------
# Hotels: by city → hotelIds → offers
# -----------------------------
def _hotels_by_city(city_code: str, limit: int = 30) -> List[str]:
    """
    Get a list of hotel IDs for a given city code.
    """
    if not city_code:
        return []
    try:
        r = requests.get(
            f"{AMADEUS_BASE}/v1/reference-data/locations/hotels/by-city",
            params={"cityCode": city_code.upper(), "page[limit]": max(1, min(limit, 100))},
            headers=_auth_headers(),
            timeout=20,
        )
        if r.status_code >= 400:
            return []
        data = r.json().get("data", [])
        hotel_ids = [h.get("hotelId") for h in data if h.get("hotelId")]
        # Deduplicate & truncate
        return list(dict.fromkeys(hotel_ids))[:limit]
    except Exception:
        return []


def hotel_offers(city_code: str,
                 checkin: Optional[str],
                 checkout: Optional[str],
                 adults: int = 1,
                 currency: str = "EUR",
                 max_hotels: int = 20) -> Dict[str, Any]:
    """
    For a city (e.g., PAR), get hotelIds then pull offers.
    Returns raw JSON from /v3/shopping/hotel-offers (or {"data": []}).
    """
    hotel_ids = _hotels_by_city(city_code, limit=max_hotels)
    if not hotel_ids:
        return {"data": []}

    # Build params (Amadeus prefers these exact names)
    params = {
        "hotelIds": ",".join(hotel_ids),
        "adults": max(1, adults),
        "currency": currency.upper(),
    }
    # Dates are strongly recommended for real prices
    if checkin:
        params["checkInDate"] = checkin
    if checkout:
        params["checkOutDate"] = checkout

    try:
        r = requests.get(
            f"{AMADEUS_BASE}/v3/shopping/hotel-offers",
            params=params,
            headers=_auth_headers(),
            timeout=25,
        )
        if r.status_code >= 400:
            return {"data": [], "error": f"{r.status_code} {r.text}"}
        return r.json()
    except Exception as e:
        return {"data": [], "error": str(e)}


# -----------------------------
# Normalize hotel offers
# -----------------------------
def normalize_hotels(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert /v3/shopping/hotel-offers response into a simple list like:
      { name, stars, neighborhood, price_total, price_currency, deep_link }
    Chooses the cheapest offer per hotel.
    """
    out: List[Dict[str, Any]] = []
    if not resp or not isinstance(resp, dict):
        return out

    data = resp.get("data") or []
    if not isinstance(data, list):
        return out

    for entry in data:
        hotel = entry.get("hotel") or {}
        offers = entry.get("offers") or []
        if not offers:
            continue

        # find cheapest offer for this hotel
        cheapest = None
        cheapest_amt = 1e18
        for off in offers:
            price = (off.get("price") or {})
            try:
                amt = float(price.get("total") or price.get("base") or 1e18)
            except Exception:
                amt = 1e18
            if amt < cheapest_amt:
                cheapest_amt = amt
                cheapest = off

        if not cheapest or cheapest_amt >= 1e18:
            continue

        name = hotel.get("name") or "Hotel"
        stars_raw = hotel.get("rating")
        try:
            stars = int(stars_raw) if stars_raw is not None else None
        except Exception:
            stars = None

        address = hotel.get("address") or {}
        city = address.get("cityName")
        neighborhood = hotel.get("iataCode") or city

        price_obj = cheapest.get("price") or {}
        price_total = float(price_obj.get("total") or price_obj.get("base") or 0.0)
        price_ccy = (price_obj.get("currency") or "EUR").upper()

        # Deep link: use the offer ID to link to the API resource (sandbox)
        oid = cheapest.get("id")
        deep_link = f"{AMADEUS_BASE}/v3/shopping/hotel-offers/{oid}" if oid else None

        out.append({
            "name": name,
            "stars": stars,
            "neighborhood": neighborhood,
            "price_total": price_total,
            "price_currency": price_ccy,
            "deep_link": deep_link,
        })

    # sort cheapest first
    out.sort(key=lambda x: x["price_total"])
    return out


# -----------------------------
# Pretty "City, Country (CODE)" for printing
# -----------------------------
@lru_cache(maxsize=256)
def city_country_for_code(code: str) -> str:
    """
    Given an IATA city or airport code (e.g., LON, LHR, CDG),
    return 'City, Country (CODE)' or just '(CODE)' if unknown.
    """
    code = (code or "").upper().strip()
    if not code:
        return "UNKNOWN"

    try:
        r = requests.get(
            f"{AMADEUS_BASE}/v1/reference-data/locations",
            params={"subType": "CITY,AIRPORT", "keyword": code, "page[limit]": 10},
            headers=_auth_headers(),
            timeout=20,
        )
        if r.status_code >= 400:
            return f"{code}"

        data = r.json().get("data", [])
        if not data:
            return f"{code}"

        # Prefer exact code match
        for item in data:
            if item.get("iataCode", "").upper() == code:
                name = item.get("name") or item.get("detailedName") or item.get("iataCode")
                addr = item.get("address") or {}
                city = (addr.get("cityName") or name or code).replace(" Metropolitan Area", "")
                country = addr.get("countryName") or ""
                return f"{city}, {country} ({code})" if country else f"{city} ({code})"

        # Else first item
        item = data[0]
        name = item.get("name") or item.get("detailedName") or item.get("iataCode")
        addr = item.get("address") or {}
        city = (addr.get("cityName") or name or code).replace(" Metropolitan Area", "")
        country = addr.get("countryName") or ""
        return f"{city}, {country} ({code})" if country else f"{city} ({code})"
    except Exception:
        return f"{code}"
