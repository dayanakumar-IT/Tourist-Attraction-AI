# live_sources.py
# Async helpers used by Scam Watcher + Safety/Policy agents

import os
import datetime
from urllib.parse import urlparse, quote_plus
from typing import Optional, Tuple

import httpx

# -------------------------------------------------------------------
# Env keys (leave blank -> function returns None and pipeline degrades gracefully)
# -------------------------------------------------------------------
GSB_KEY = os.getenv("GSB_KEY") or ""
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY") or ""
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY") or ""
DEBUG_LIVE = os.getenv("DEBUG_LIVE", "0") == "1"   # set DEBUG_LIVE=1 to print debug lines


# =========================
# URL / DOMAIN CHECKS
# =========================

def extract_domain(host_or_url: str) -> Optional[str]:
    """Return domain/host from URL or host string (lowercased)."""
    try:
        netloc = urlparse(host_or_url).netloc or host_or_url
        return netloc.split("@")[-1].split(":")[0].lower()
    except Exception:
        return None


async def rdap_domain_age_days(domain: str) -> Optional[int]:
    """RDAP (no key). Returns age in days or None."""
    url = f"https://rdap.org/domain/{domain}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            if r.status_code != 200:
                if DEBUG_LIVE: print("[RDAP] HTTP", r.status_code, domain)
                return None
            data = r.json()
            for ev in data.get("events", []):
                if ev.get("eventAction") == "registration":
                    dt = ev.get("eventDate")
                    if not dt:
                        continue
                    reg = datetime.datetime.fromisoformat(dt.replace("Z", "+00:00"))
                    age = (datetime.datetime.now(datetime.timezone.utc) - reg).days
                    if DEBUG_LIVE: print("[RDAP] age days =", age, domain)
                    return int(age)
    except Exception as e:
        if DEBUG_LIVE: print("[RDAP] error:", e)
        return None
    return None


async def gsb_is_malicious(url: str) -> Optional[bool]:
    """
    Google Safe Browsing quick check.
    Returns True/False, or None if no key/failed.
    """
    if not GSB_KEY:
        return None
    payload = {
        "client": {"clientId": "tourismAI", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GSB_KEY}",
                json=payload,
            )
            if r.status_code != 200:
                if DEBUG_LIVE: print("[GSB] HTTP", r.status_code, url)
                return None
            data = r.json()
            hit = bool(data.get("matches"))
            if DEBUG_LIVE: print("[GSB] malicious:", hit, url)
            return hit
    except Exception as e:
        if DEBUG_LIVE: print("[GSB] error:", e)
        return None


# =========================
# GOOGLE PLACES / PRICE
# =========================

_PRICE_LEVEL_TO_MEDIAN = {
    0: 0.0,    # free
    1: 10.0,   # inexpensive
    2: 25.0,   # moderate
    3: 60.0,   # expensive
    4: 120.0,  # very expensive
}

async def _places_text_search(city: str, name: str) -> Optional[str]:
    """Return first place_id for query 'name city'."""
    if not GOOGLE_MAPS_KEY:
        return None
    q = quote_plus(f"{name} {city}".strip())
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={q}&key={GOOGLE_MAPS_KEY}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            s = await client.get(url)
            if s.status_code != 200:
                if DEBUG_LIVE: print("[PLACES search] HTTP", s.status_code, name, city)
                return None
            results = s.json().get("results", [])
            if not results:
                if DEBUG_LIVE: print("[PLACES search] no results", name, city)
                return None
            place_id = results[0].get("place_id")
            return place_id
    except Exception as e:
        if DEBUG_LIVE: print("[PLACES search] error:", e)
        return None


async def google_place_official_website(city: str, name: str) -> Optional[str]:
    """Uses Places Text Search -> Details to get official website; requires GOOGLE_MAPS_KEY."""
    if not GOOGLE_MAPS_KEY:
        return None
    place_id = await _places_text_search(city, name)
    if not place_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            d = await client.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={"place_id": place_id, "fields": "website,url", "key": GOOGLE_MAPS_KEY},
            )
            if d.status_code != 200:
                if DEBUG_LIVE: print("[PLACES details] HTTP", d.status_code, place_id)
                return None
            details = d.json().get("result", {})
            website = details.get("website")
            if DEBUG_LIVE: print("[PLACES website]", website)
            return website
    except Exception as e:
        if DEBUG_LIVE: print("[PLACES details] error:", e)
        return None


async def google_place_price_median(city: str, name: str) -> Optional[float]:
    """Derive a median-ish price from Google price_level (0-4)."""
    if not GOOGLE_MAPS_KEY:
        return None
    place_id = await _places_text_search(city, name)
    if not place_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            d = await client.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={"place_id": place_id, "fields": "price_level", "key": GOOGLE_MAPS_KEY},
            )
            if d.status_code != 200:
                if DEBUG_LIVE: print("[PLACES price] HTTP", d.status_code, place_id)
                return None
            level = d.json().get("result", {}).get("price_level")
            if level is None:
                if DEBUG_LIVE: print("[PLACES price] no price_level")
                return None
            median = _PRICE_LEVEL_TO_MEDIAN.get(int(level))
            if DEBUG_LIVE: print("[PLACES price] level -> median", level, "->", median)
            return median
    except Exception as e:
        if DEBUG_LIVE: print("[PLACES price] error:", e)
        return None


# =========================
# WEATHER / ADVISORY
# =========================

async def openweather_advisory(city: str) -> Optional[str]:
    """
    Return a short weather safety tip for the city, or None.
    Uses current weather; keep messages short and actionable.
    """
    if not OPENWEATHER_KEY or not city:
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": OPENWEATHER_KEY, "units": "metric"},
            )
            if r.status_code != 200:
                if DEBUG_LIVE: print("[WX] HTTP", r.status_code, city)
                return None
            data = r.json()
    except Exception as e:
        if DEBUG_LIVE: print("[WX] error:", e)
        return None

    weather_list = data.get("weather") or [{}]
    main = (weather_list[0] or {}).get("main", "") or ""
    desc = (weather_list[0] or {}).get("description", "") or ""
    temp = (data.get("main") or {}).get("feels_like")
    wind = (data.get("wind") or {}).get("speed")

    if DEBUG_LIVE:
        print("[WX]", city, "main:", main, "desc:", desc, "temp:", temp, "wind:", wind)

    tips: list[str] = []
    m = main.lower()
    if m in {"rain", "thunderstorm", "drizzle"}:
        tips.append("Rain expected—carry a raincoat; waterproof your devices.")
    if m == "snow":
        tips.append("Snow/ice risk—allow extra travel time and wear proper shoes.")
    if isinstance(temp, (int, float)) and temp >= 35:
        tips.append("High heat—hydrate often and avoid midday sun.")
    if isinstance(wind, (int, float)) and wind >= 12:  # ~40+ km/h
        tips.append("Strong wind—secure hats/umbrellas near viewpoints/coast.")

    return tips[0] if tips else None



async def travel_advisory(country_code: str) -> Optional[Tuple[float, str]]:
    """
    Returns (score, message) or None. Score ~0(safe) .. 5(risky).
    No key required.
    """
    if not country_code:
        return None
    cc = (country_code or "").upper()
    url = f"https://www.travel-advisory.info/api?countrycode={cc}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            if r.status_code != 200:
                if DEBUG_LIVE: print("[TA] HTTP", r.status_code, cc)
                return None
            data = r.json()
            info = (data.get("data", {}).get(cc, {})).get("advisory", {})
            score = info.get("score")
            msg = info.get("message") or ""
            if score is None:
                return None
            if DEBUG_LIVE: print("[TA]", cc, "score:", score, "msg:", msg[:80])
            return float(score), msg
    except Exception as e:
        if DEBUG_LIVE: print("[TA] error:", e)
        return None
