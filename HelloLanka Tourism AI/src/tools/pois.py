# src/tools/pois.py
"""
Google Places-only POI tools + LLM-based experience normalization.

Public functions kept for backward-compat with your existing pipeline:
- search_radius(lat, lon, kinds, radius=6000, limit=6)
- search_radius_general_filtered(lat, lon, include_name_regex, radius=6000, limit=20)
- search_radius_name_filtered_multi(lat, lon, include_name_regex, radii=[...], per_radius_limit=40)

New helpers for your input_demo.json / frontend simulation:
- infer_kinds_from_text(free_text: str) -> List[str]
- get_pois_for_text(lat, lon, free_text, radius=6000, limit=20) -> List[Dict]

Notes:
- If GEMINI is unavailable, infer_kinds_from_text falls back to fast regex heuristics.
- Unknown experience words still work via a keyword fallback so nothing crashes.
"""
from __future__ import annotations

import re
import time
import requests
from typing import List, Dict, Any, Optional, Tuple, Set

# ---- settings (expects you already load .env in src/settings.py) ----
from ..settings import (
    GOOGLE_PLACES_API_KEY,
    HTTP_TIMEOUT,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)

_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

# A small, extensible taxonomy of domain “kinds” your planner understands.
# Left side = normalized kind tag you use internally.
# Right side = (Google Places 'type', keyword pattern) to retrieve relevant POIs.
_KIND_TO_GOOGLE: Dict[str, Tuple[Optional[str], str]] = {
    # coastal / nature
    "beaches":      ("tourist_attraction", "beach"),
    "natural":      ("natural_feature",    "park|nature|forest|waterfall|lake|river|mountain"),
    "waterfalls":   ("natural_feature",    "waterfall"),
    "view_points":  ("tourist_attraction", "viewpoint|scenic|lookout|sunset point"),
    "wildlife":     ("zoo",                "wildlife|safari|elephant|turtle"),
    "hiking":       ("tourist_attraction", "trail|hiking"),
    "gardens":      ("park",               "botanical|garden|arboretum"),
    # culture / history / religion
    "historical":   ("tourist_attraction", "fort|museum|ruins|heritage|colonial"),
    "museums":      ("museum",             ""),
    "religious":    ("place_of_worship",   "temple|kovil|church|mosque|stupa|vihara|shrine"),
    "culture":      ("tourist_attraction", "cultural|dance|craft|handloom|market"),
    # food / leisure
    "food":         ("restaurant",         "restaurant|local food|sri lankan|seafood"),
    "nightlife":    ("bar",                "nightlife|pub|club|bar"),
    "shopping":     ("shopping_mall",      "market|bazaar|souvenir|mall"),
    "spa":          ("spa",                "spa|ayurveda|massage|wellness"),
    # family / kids
    "family":       ("tourist_attraction", "family|kids|playground|park"),
    "kids":         ("tourist_attraction", "kids|playground"),
}

# Lightweight synonyms (for non-LLM fallback)
_SYNONYMS: Dict[str, str] = {
    r"\bbeach(es)?\b": "beaches",
    r"\bwaterfall(s)?\b": "waterfalls",
    r"\b(view\s?point|scenic|lookout)\b": "view_points",
    r"\b(hike|hiking|trail)\b": "hiking",
    r"\b(wildlife|safari|elephant|turtle)\b": "wildlife",
    r"\b(garden|botanical)\b": "gardens",
    r"\b(museum|museums)\b": "museums",
    r"\b(fort|colonial|heritage|ruins)\b": "historical",
    r"\b(temple|kovil|church|mosque|stupa|vihara|shrine)\b": "religious",
    r"\b(food|restaurant|cafe|seafood)\b": "food",
    r"\b(nightlife|pub|bar|club)\b": "nightlife",
    r"\b(shop|shopping|market|bazaar|souvenir|mall)\b": "shopping",
    r"\b(spa|massage|ayurveda|wellness)\b": "spa",
    r"\b(nature|forest|lake|river|mountain)\b": "natural",
    r"\b(kid|kids|family)\b": "family",
    r"\b(culture|cultural|dance|craft|handloom)\b": "culture",
}

# ---------------- Google Places core ----------------

def _assert_key():
    if not GOOGLE_PLACES_API_KEY:
        raise RuntimeError("Missing GOOGLE_PLACES_API_KEY in .env")

def _gp_call(
    lat: float,
    lon: float,
    radius_m: int,
    type_opt: Optional[str],
    keyword: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Google Places Nearby Search with minimal pagination.
    - radius <= 50,000 m
    - If `keyword` empty, we still pass a type to stay broad but relevant.
    """
    _assert_key()
    collected: List[Dict[str, Any]] = []
    pagetoken: Optional[str] = None
    radius_m = min(int(radius_m), 50000)
    limit = int(max(limit, 1))

    while True:
        if pagetoken:
            params = {"key": GOOGLE_PLACES_API_KEY, "pagetoken": pagetoken}
        else:
            params = {
                "key": GOOGLE_PLACES_API_KEY,
                "location": f"{lat},{lon}",
                "radius": radius_m,
                "keyword": keyword or "",
            }
            if type_opt:
                params["type"] = type_opt

        r = requests.get(_NEARBY_URL, params=params, timeout=HTTP_TIMEOUT)
        if not r.ok:
            raise RuntimeError(f"Google Places error {r.status_code}: {r.text}")

        data = r.json() or {}
        status = data.get("status")
        if status == "ZERO_RESULTS":
            break
        if status not in ("OK", "ZERO_RESULTS"):
            # e.g. OVER_QUERY_LIMIT, REQUEST_DENIED, INVALID_REQUEST
            msg = data.get("error_message", "")
            raise RuntimeError(f"Google Places status={status} {msg}")

        for place in data.get("results", []):
            collected.append({
                "name": place.get("name"),
                "point": {
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lon": place.get("geometry", {}).get("location", {}).get("lng"),
                },
                "types": place.get("types", []),
                "place_id": place.get("place_id"),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                # keep a 'kinds' string for downstream compatibility
                "kinds": ",".join(place.get("types", [])),
            })
            if len(collected) >= limit:
                return collected

        pagetoken = data.get("next_page_token")
        if not pagetoken:
            break
        # Next page tokens need a short delay to become valid
        time.sleep(0.5)  # Reduced from 2 seconds

    return collected

def _from_kinds(kinds: List[str]) -> Tuple[Optional[str], str]:
    """
    Combine several normalized kinds into a single (type, keyword) query.
    We pick the first available 'type' and OR-join all related keywords.
    """
    chosen_type: Optional[str] = None
    keywords: List[str] = []
    for k in kinds:
        t, kw = _KIND_TO_GOOGLE.get(k, ("tourist_attraction", k))
        if t and not chosen_type:
            chosen_type = t
        if kw:
            keywords.append(kw)
    keyword = "|".join(keywords) if keywords else ""
    return chosen_type, keyword

# ---------------- LLM normalization ----------------

def _infer_with_gemini(free_text: str) -> List[str]:
    """
    Use Gemini to map arbitrary user text to a subset of normalized kinds.
    Returns a list like ['beaches','spa','food'] (subset of _KIND_TO_GOOGLE keys).
    """
    if not GEMINI_API_KEY:
        return []

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model_name = GEMINI_MODEL or "gemini-2.0-flash"
        model = genai.GenerativeModel(model_name)

        # Keep prompt short, deterministic, and JSON-only.
        taxonomy = ", ".join(sorted(_KIND_TO_GOOGLE.keys()))
        prompt = f"""
You are a classifier. From the user text, select 1-5 most relevant tags strictly from this allowed list:
[{taxonomy}]
Return ONLY a JSON array of strings. No prose.

User text: {free_text}
"""
        resp = model.generate_content(prompt)
        txt = (resp.text or "").strip()
        # robust JSON-ish extraction
        import json
        start = txt.find("[")
        end = txt.rfind("]")
        if start != -1 and end != -1 and end > start:
            arr = json.loads(txt[start:end+1])
            if isinstance(arr, list):
                out = []
                for item in arr:
                    if isinstance(item, str) and item in _KIND_TO_GOOGLE:
                        out.append(item)
                return list(dict.fromkeys(out))[:5]  # unique, max 5
        return []
    except Exception:
        # If anything fails (no package, rate limits, etc.), fall back to regex
        return []

def _infer_with_regex(free_text: str) -> List[str]:
    s = free_text.lower()
    found: List[str] = []
    for pat, tag in _SYNONYMS.items():
        if re.search(pat, s, flags=re.IGNORECASE):
            found.append(tag)
    # Always dedupe, keep order
    deduped = list(dict.fromkeys(found))
    return deduped[:5] if deduped else []

def infer_kinds_from_text(free_text: str) -> List[str]:
    """
    Public: normalize arbitrary user text to your internal 'kinds'.
    Strategy: Gemini → regex heuristics → default ['tourist_attraction' via keyword fallback at callsite]
    """
    kinds = _infer_with_gemini(free_text)
    if not kinds:
        kinds = _infer_with_regex(free_text)
    return kinds

# ---------------- Public API (backward-compatible) ----------------

def search_radius(lat: float, lon: float, kinds: List[str], radius=6000, limit=6) -> List[Dict[str, Any]]:
    """
    Kinds-based POI search using Google Places Nearby.
    If 'kinds' is empty, this will raise (same behavior you had before).
    """
    if not kinds:
        raise ValueError("kinds list is empty; use infer_kinds_from_text() or search_radius_general_filtered()")
    t, kw = _from_kinds(kinds)
    data = _gp_call(lat, lon, radius, t, kw, max(int(limit), 6))
    if not data:
        raise ValueError(f"No POIs returned for {lat},{lon} kinds={','.join(kinds)}")
    return data

def search_radius_general_filtered(lat: float, lon: float, include_name_regex: str, radius=6000, limit=20) -> List[Dict[str, Any]]:
    """
    Broad query (tourist_attraction) then filter by regex on name.
    Useful when you don't have normalized kinds yet.
    """
    pat = re.compile(include_name_regex, re.IGNORECASE)
    data = _gp_call(lat, lon, radius, "tourist_attraction", "", int(limit))
    filtered = [p for p in data if pat.search(p.get("name") or "")]
    if not filtered:
        raise ValueError(f"No POIs matched name filter /{include_name_regex}/ near {lat},{lon}")
    return filtered

def search_radius_name_filtered_multi(
    lat: float,
    lon: float,
    include_name_regex: str,
    radii: List[int] = [6000, 10000, 15000],
    per_radius_limit: int = 40,
) -> List[Dict[str, Any]]:
    """
    Try multiple radii; return first non-empty set matching the regex.
    """
    pat = re.compile(include_name_regex, re.IGNORECASE)
    for r_m in radii:
        data = _gp_call(lat, lon, r_m, "tourist_attraction", "", int(per_radius_limit))
        filtered = [p for p in data if pat.search(p.get("name") or "")]
        if filtered:
            return filtered
    return []

# ---------------- Convenience for your input_demo.json ----------------

def get_pois_for_text(
    lat: float,
    lon: float,
    free_text: str,
    radius: int = 10000,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """
    One-shot helper:
    - infer kinds from arbitrary user text (LLM → regex)
    - fetch POIs per kind (merged & de-duped)
    - if still sparse, run one broad keyword-only query with the raw text

    This makes your backend simulation easy:
    kinds = infer_kinds_from_text("Beach, spa and good food")  # -> ['beaches','spa','food']
    pois  = get_pois_for_text(lat, lon, "Beach, spa and good food")
    """
    kinds = infer_kinds_from_text(free_text)
    seen_ids: Set[str] = set()
    merged: List[Dict[str, Any]] = []

    if kinds:
        t, kw = _from_kinds(kinds)
        data = _gp_call(lat, lon, radius, t, kw, limit)
        for p in data:
            pid = p.get("place_id") or f"{p.get('name')}@{p.get('point')}"
            if pid not in seen_ids:
                merged.append(p); seen_ids.add(pid)

    # Fallback: keyword-only search to catch odd phrasings
    if len(merged) < max(5, limit // 3):
        data2 = _gp_call(lat, lon, radius, "tourist_attraction", free_text, limit)
        for p in data2:
            pid = p.get("place_id") or f"{p.get('name')}@{p.get('point')}"
            if pid not in seen_ids:
                merged.append(p); seen_ids.add(pid)

    # Cap to requested limit
    if len(merged) > limit:
        merged = merged[:limit]
    return merged
