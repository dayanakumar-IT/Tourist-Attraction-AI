# src/tools/weather.py
from __future__ import annotations

import datetime as dt
import time
from typing import Dict, Any, List, Optional

import requests

from ..settings import OPENWEATHER_API_KEY, HTTP_TIMEOUT

_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"  # 5-day / 3-hourly


def _require_key():
    if not OPENWEATHER_API_KEY:
        raise RuntimeError("Missing OPENWEATHER_API_KEY in .env")


def _fetch_forecast(lat: float, lon: float, retries: int = 2) -> Dict[str, Any]:
    """Fetch OpenWeather 5-day/3-hourly forecast with simple retries."""
    _require_key()
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(_FORECAST_URL, params=params, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            return r.json() or {}
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
            else:
                raise RuntimeError(f"OpenWeather fetch failed after retries: {e}") from e
    # not reached
    raise RuntimeError(f"OpenWeather fetch failed: {last_err}")


def _group_slots_by_date(slots: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group 3-hourly slots by YYYY-MM-DD of dt_txt."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for s in slots:
        key = (s.get("dt_txt") or "")[:10]
        if key:
            grouped.setdefault(key, []).append(s)
    return grouped


def _agg_day(slots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate a day's worth of 3-hourly slots into a compact hint."""
    temps = [s.get("main", {}).get("temp") for s in slots if isinstance(s.get("main", {}).get("temp"), (int, float))]
    wind = [s.get("wind", {}).get("speed") for s in slots if isinstance(s.get("wind", {}).get("speed"), (int, float))]
    pops = [s.get("pop") for s in slots if isinstance(s.get("pop"), (int, float))]
    rain_3h = []
    for s in slots:
        r = s.get("rain", {})
        if isinstance(r, dict):
            v = r.get("3h") or r.get("1h")
            if isinstance(v, (int, float)):
                rain_3h.append(float(v))
    snow_3h = []
    for s in slots:
        sn = s.get("snow", {})
        if isinstance(sn, dict):
            v = sn.get("3h") or sn.get("1h")
            if isinstance(v, (int, float)):
                snow_3h.append(float(v))

    total_precip = sum(rain_3h) + sum(snow_3h)
    max_pop = max(pops) if pops else 0.0
    tmin = min(temps) if temps else None
    tmax = max(temps) if temps else None
    wmax = max(wind) if wind else None

    # Derive a simple summary
    if total_precip > 0.0 or max_pop >= 0.5:
        summary = "rainy"
    else:
        summary = "clear"

    # Try to pick a representative icon/condition from the midday slot
    rep_cond = None
    for s in slots:
        if s.get("dt_txt", "").endswith("12:00:00"):
            arr = s.get("weather") or []
            if arr and isinstance(arr, list):
                rep_cond = arr[0].get("main")  # e.g., Rain, Clouds, Clear
            break
    if not rep_cond and slots:
        arr = slots[0].get("weather") or []
        if arr and isinstance(arr, list):
            rep_cond = arr[0].get("main")

    return {
        "summary": summary,                 # "clear" | "rainy" (simple hint for planner)
        "condition": rep_cond,              # e.g., "Clouds", "Rain", "Clear"
        "temp_min_c": tmin,
        "temp_max_c": tmax,
        "wind_max_ms": wmax,
        "precip_mm": round(total_precip, 1),
        "pop_max": round(max_pop, 2),
        "slots_count": len(slots),
    }


def forecast_hint(lat: float, lon: float, date: dt.date) -> Dict[str, Any]:
    """
    Return a compact weather hint for a given date near the given lat/lon.

    - Uses OpenWeather 5-day/3-hourly forecast.
    - If requested date is outside the 5-day window, picks the *closest* available day.
    - Aggregates temp min/max, max wind, total precipitation, and max probability of precipitation.
    """
    if not isinstance(date, dt.date):
        raise ValueError("date must be a datetime.date")

    data = _fetch_forecast(lat, lon)
    slots = data.get("list", []) or []
    if not slots:
        raise ValueError("No forecast data returned")

    grouped = _group_slots_by_date(slots)
    if not grouped:
        raise ValueError("No dated forecast slots found")

    target = date.strftime("%Y-%m-%d")
    if target not in grouped:
        # Choose the closest day present in the 5-day window
        # Collect available dates and pick minimal absolute delta
        avail_keys = sorted(grouped.keys())
        # Convert to date objects
        avail_dates = [dt.datetime.strptime(k, "%Y-%m-%d").date() for k in avail_keys]
        deltas = [abs((ad - date).days) for ad in avail_dates]
        best_idx = deltas.index(min(deltas))
        target = avail_keys[best_idx]

    day_slots = grouped.get(target, [])
    if not day_slots:
        raise ValueError(f"No weather slots found for {target}")

    agg = _agg_day(day_slots)
    agg["date"] = target
    return agg


def diag_test_openweather(lat: float, lon: float, date: dt.date):
    """Minimal probe used by orchestrator --diag."""
    _ = forecast_hint(lat, lon, date)
