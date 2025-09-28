# providers/booking_api.py
import os
import requests
from typing import Any, Dict, List, Optional

# If you want, also load .env here as a belt-and-suspenders:
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_URL = "https://booking-com.p.rapidapi.com/v1"
HOST = "booking-com.p.rapidapi.com"

def _headers() -> Dict[str, str]:
    key = os.getenv("RAPIDAPI_KEY")  # read at call-time (not at import)
    if not key:
        raise RuntimeError("Missing RAPIDAPI_KEY in environment")
    return {
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": HOST,
    }

# ---------- Destinations ----------
def find_city_dest_id(name: str, locale: str = "en-gb") -> Optional[str]:
    if not name:
        return None
    url = f"{BASE_URL}/hotels/locations"
    params = {"name": name, "locale": locale}
    r = requests.get(url, headers=_headers(), params=params, timeout=20)
    if r.status_code >= 400:
        return None
    data = r.json()
    for item in data:
        if (item.get("dest_type") or "").lower() == "city":
            return item.get("dest_id")
    if data:
        return data[0].get("dest_id")
    return None

# ---------- Hotel search ----------
def booking_hotel_search_city(dest_id: str,
                              checkin: str,
                              checkout: str,
                              adults: int = 1,
                              currency: str = "USD",
                              locale: str = "en-gb",
                              order_by: str = "price",
                              page_number: int = 0) -> Dict[str, Any]:
    url = f"{BASE_URL}/hotels/search"
    params = {
        "checkin_date": checkin,
        "checkout_date": checkout,
        "dest_id": dest_id,
        "dest_type": "city",
        "adults_number": max(1, int(adults)),
        "order_by": order_by,
        "locale": locale,
        "units": "metric",
        "filter_by_currency": currency,
        "page_number": page_number,
    }
    r = requests.get(url, headers=_headers(), params=params, timeout=30)
    if r.status_code >= 400:
        return {"result": [], "error": f"{r.status_code} {r.text}"}
    return r.json()

# ---------- Normalizer ----------
def normalize_booking_hotels(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not resp:
        return out

    results = resp.get("result") or []
    for h in results:
        name = h.get("hotel_name") or h.get("hotel_name_trans") or "Hotel"
        stars = None
        try:
            cls = h.get("class")
            if cls is not None:
                stars = int(round(float(cls)))
        except Exception:
            stars = None

        neighborhood = h.get("district") or h.get("city_trans") or h.get("city") or None

        price_total = None
        price_currency = (h.get("currencycode") or "USD").upper()
        pb = h.get("price_breakdown") or {}
        try:
            if "all_inclusive_price" in pb:
                price_total = float(pb["all_inclusive_price"])
        except Exception:
            pass
        if price_total is None:
            try:
                price_total = float(h.get("min_total_price"))
            except Exception:
                continue

        deep_link = h.get("url")

        out.append({
            "name": name,
            "stars": stars,
            "neighborhood": neighborhood,
            "price_total": price_total,
            "price_currency": price_currency,
            "deep_link": deep_link,
        })

    out.sort(key=lambda x: x["price_total"])
    return out[:10]
