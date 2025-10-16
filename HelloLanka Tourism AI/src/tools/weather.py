# src/tools/weather.py
import requests, datetime as dt
from typing import Dict, Any
from ..settings import OPENWEATHER_API_KEY, HTTP_TIMEOUT

def forecast_hint(lat: float, lon: float, date: dt.date) -> Dict[str, Any]:
    if not OPENWEATHER_API_KEY:
        raise RuntimeError("Missing OPENWEATHER_API_KEY in .env")
    r = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"},
        timeout=HTTP_TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"OpenWeather error {r.status_code}: {r.text}")
    data = r.json()
    target = date.strftime("%Y-%m-%d")
    slots = [x for x in data.get("list", []) if x.get("dt_txt", "").startswith(target)]
    if not slots:
        raise ValueError(f"No weather slots found for {target}")
    has_rain = any("rain" in (s.get("weather",[{}])[0].get("main","").lower()) for s in slots)
    return {"summary": "rainy" if has_rain else "clear", "rain_mm": 6 if has_rain else 0}

def diag_test_openweather(lat: float, lon: float, date: dt.date):
    """Minimal probe used by orchestrator --diag."""
    _ = forecast_hint(lat, lon, date)
