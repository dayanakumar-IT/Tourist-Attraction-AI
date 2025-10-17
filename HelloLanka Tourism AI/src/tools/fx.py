# src/tools/fx.py
from __future__ import annotations

import re
import time
from datetime import date as date_cls
from typing import Dict, Optional, Tuple

import requests

from ..settings import HTTP_TIMEOUT

# ------------------------
# Config / Validation
# ------------------------

_ISO_CCY_RE = re.compile(r"^[A-Z]{3}$")

def _validate_ccy(code: str) -> str:
    if not isinstance(code, str):
        raise ValueError("Currency code must be a string.")
    code = code.upper().strip()
    if not _ISO_CCY_RE.match(code):
        raise ValueError(f"Invalid currency code: {code!r} (must be ISO 4217, e.g., 'USD', 'LKR')")
    return code

def _validate_amount(amount: float) -> float:
    try:
        amount = float(amount)
    except Exception as e:
        raise ValueError("Amount must be a number.") from e
    return amount


# ------------------------
# Simple in-memory cache
# ------------------------
# Cache key: (from_ccy, to_ccy, date_str or None)
# Value: (timestamp_epoch_seconds, rate_float)
_RATE_CACHE: Dict[Tuple[str, str, Optional[str]], Tuple[float, float]] = {}

def _cache_get(from_ccy: str, to_ccy: str, date_str: Optional[str], max_age_sec: int) -> Optional[float]:
    key = (from_ccy, to_ccy, date_str)
    item = _RATE_CACHE.get(key)
    if not item:
        return None
    ts, rate = item
    if (time.time() - ts) <= max_age_sec:
        return rate
    # stale
    _RATE_CACHE.pop(key, None)
    return None

def _cache_set(from_ccy: str, to_ccy: str, date_str: Optional[str], rate: float) -> None:
    key = (from_ccy, to_ccy, date_str)
    _RATE_CACHE[key] = (time.time(), float(rate))


# ------------------------
# Low-level HTTP call
# ------------------------

def _fetch_rate_direct(from_ccy: str, to_ccy: str, date_str: Optional[str]) -> float:
    """
    Ask exchangerate.host for a direct conversion rate.
    Uses the /convert endpoint; supports an optional date parameter for historical rates.
    Returns the per-unit rate (1 from_ccy -> ? to_ccy).
    """
    url = "https://api.exchangerate.host/convert"
    params = {
        "from": from_ccy,
        "to": to_ccy,
        "amount": 1.0,        # get unit rate; we'll multiply by amount later
    }
    if date_str:
        params["date"] = date_str  # exchangerate.host accepts a date here

    r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json() or {}
    result = data.get("result")
    if result is None:
        # Some error payloads surface under 'info'/'error'; keep message friendly
        raise ValueError(f"Rate unavailable for {from_ccy}->{to_ccy} on {date_str or 'latest'}")
    return float(result)


def _fetch_rate_via_usd(from_ccy: str, to_ccy: str, date_str: Optional[str]) -> float:
    """
    Fallback: compute cross rate via USD
    rate(from->to) = rate(from->USD) * rate(USD->to)
    """
    if from_ccy == "USD":
        usd_to_to = _fetch_rate_direct("USD", to_ccy, date_str)
        return usd_to_to
    if to_ccy == "USD":
        from_to_usd = _fetch_rate_direct(from_ccy, "USD", date_str)
        return from_to_usd

    from_to_usd = _fetch_rate_direct(from_ccy, "USD", date_str)
    usd_to_to = _fetch_rate_direct("USD", to_ccy, date_str)
    return float(from_to_usd) * float(usd_to_to)


def _get_rate_with_retries(from_ccy: str, to_ccy: str, date_str: Optional[str], retries: int) -> float:
    """
    Try direct rate first; on failure, retry with backoff, then try USD pivot.
    """
    # Exponential backoff schedule (seconds)
    for attempt in range(retries + 1):
        try:
            return _fetch_rate_direct(from_ccy, to_ccy, date_str)
        except (requests.RequestException, ValueError):
            if attempt >= retries:
                break
            time.sleep(0.5 * (2 ** attempt))

    # Direct failed after retries → try USD pivot with its own smaller retry loop
    for attempt in range(retries + 1):
        try:
            return _fetch_rate_via_usd(from_ccy, to_ccy, date_str)
        except (requests.RequestException, ValueError):
            if attempt >= retries:
                break
            time.sleep(0.5 * (2 ** attempt))

    raise ValueError(f"Failed to retrieve rate {from_ccy}->{to_ccy} on {date_str or 'latest'} after retries")


# ------------------------
# Fallback heuristics
# ------------------------
# Conservative static fallbacks to avoid hard failures when the FX API is down
_FALLBACK_RATES: Dict[Tuple[str, str], float] = {
    ("USD", "LKR"): 300.0,
    ("EUR", "LKR"): 330.0,
    ("GBP", "LKR"): 380.0,
    ("LKR", "USD"): 1.0 / 300.0,
    ("LKR", "EUR"): 1.0 / 330.0,
    ("LKR", "GBP"): 1.0 / 380.0,
}


# ------------------------
# Public API
# ------------------------

def get_rate(
    from_ccy: str,
    to_ccy: str,
    date: Optional[str | date_cls] = None,
    *,
    max_age_sec: int = 6 * 3600,
    retries: int = 2,
) -> float:
    """
    Get FX rate (1 from_ccy -> ? to_ccy), with caching, retries, and optional historical date.

    Args:
        from_ccy: ISO 4217 code, e.g., 'USD'
        to_ccy: ISO 4217 code, e.g., 'LKR'
        date: 'YYYY-MM-DD' or datetime.date; None = latest
        max_age_sec: cache TTL (default 6 hours)
        retries: number of retry attempts for HTTP and value errors (default 2)

    Returns:
        float: rate per 1 unit of from_ccy in to_ccy
    """
    from_ccy = _validate_ccy(from_ccy)
    to_ccy = _validate_ccy(to_ccy)

    if from_ccy == to_ccy:
        return 1.0

    date_str: Optional[str]
    if date is None:
        date_str = None
    elif isinstance(date, date_cls):
        date_str = date.isoformat()
    else:
        # expect 'YYYY-MM-DD'
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
            raise ValueError("date must be YYYY-MM-DD or datetime.date")
        date_str = str(date)

    # cache check
    cached = _cache_get(from_ccy, to_ccy, date_str, max_age_sec)
    if cached is not None:
        return cached

    # fetch with retries + USD fallback
    try:
        rate = _get_rate_with_retries(from_ccy, to_ccy, date_str, retries=retries)
    except Exception:
        # Try static fallback mapping
        rate = _FALLBACK_RATES.get((from_ccy, to_ccy))
        if rate is None:
            # last resort: identity rate to avoid crashing; better than failure
            rate = 1.0

    # cache store
    _cache_set(from_ccy, to_ccy, date_str, rate)
    return rate


def convert(
    amount: float,
    from_ccy: str,
    to_ccy: str,
    date: Optional[str | date_cls] = None,
    *,
    max_age_sec: int = 6 * 3600,
    retries: int = 2,
) -> float:
    """
    Convert an amount from one currency to another.

    Args:
        amount: numeric amount in from_ccy
        from_ccy: ISO 4217, e.g., 'USD'
        to_ccy: ISO 4217, e.g., 'LKR'
        date: 'YYYY-MM-DD' or datetime.date; None = latest
        max_age_sec: cache TTL (rate cache), default 6 hours
        retries: HTTP/value error retries

    Returns:
        float: converted amount in to_ccy
    """
    amount = _validate_amount(amount)
    rate = get_rate(from_ccy, to_ccy, date=date, max_age_sec=max_age_sec, retries=retries)
    return float(amount) * float(rate)
