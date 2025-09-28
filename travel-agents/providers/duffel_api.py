import os, requests
from typing import List, Dict, Any, Optional, Tuple
from schemas import FlightOption, FlightLeg

DUFFEL_BASE = "https://api.duffel.com/air"

def _headers():
    token = os.getenv("DUFFEL_ACCESS_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
    }

def _best_offers(offers: List[Dict[str, Any]], n: int = 3) -> List[Dict[str, Any]]:
    if not offers:
        return []
    return sorted(offers, key=lambda o: float(o.get("total_amount") or 1e12))[:n]

def _legs_from_slice(slc: Dict[str, Any]) -> Tuple[List[FlightLeg], int, Optional[str]]:
    legs: List[FlightLeg] = []
    segs = slc.get("segments", []) or []
    for seg in segs:
        legs.append(FlightLeg(
            carrier=(seg.get("marketing_carrier") or {}).get("name"),
            flight_number=seg.get("marketing_carrier_flight_number"),
            origin=(seg.get("origin") or {}).get("iata_code"),
            destination=(seg.get("destination") or {}).get("iata_code"),
            departure_time=seg.get("departing_at"),
            arrival_time=seg.get("arriving_at"),
            duration_iso=seg.get("duration"),
            cabin_class=seg.get("cabin_class"),
        ))
    stops = max(0, len(segs) - 1) if segs else 0
    duration_iso = slc.get("duration")
    return legs, stops, duration_iso

def _offer_request(slices: List[Dict[str, Any]], adults: int) -> Dict[str, Any]:
    body = {
        "data": {
            "slices": slices,
            "passengers": [{"type": "adult"} for _ in range(max(1, adults))],
            "max_connections": 1
        }
    }
    r = requests.post(f"{DUFFEL_BASE}/offer_requests", headers=_headers(), json=body, timeout=60)
    return {"status": r.status_code, "json": r.json(), "text": r.text}

def search_one_way_topn(origin: str, destination: str, date: str, adults: int = 1, n: int = 3) -> Dict[str, Any]:
    """
    Returns {'offers': [..up to n..], 'debug': str|None}
    """
    try:
        resp = _offer_request([{"origin": origin, "destination": destination, "departure_date": date}], adults)
        if resp["status"] >= 400:
            return {"offers": [], "debug": f"Duffel one-way {origin}->{destination} {date} HTTP {resp['status']}: {resp['text']}"}
        offers = (resp["json"].get("data") or {}).get("offers", [])
        return {"offers": _best_offers(offers, n=n), "debug": None if offers else "Duffel returned no offers"}
    except Exception as e:
        return {"offers": [], "debug": f"Exception: {e}"}

def normalize_roundtrip_pair(origin: str, destination: str,
                             out_offer: Optional[Dict[str, Any]],
                             ret_offer: Optional[Dict[str, Any]]) -> FlightOption:
    # prices
    out_price = float((out_offer or {}).get("total_amount") or 0.0)
    ret_price = float((ret_offer or {}).get("total_amount") or 0.0)
    currency = (out_offer or ret_offer or {}).get("total_currency") or "USD"
    total = (out_price if out_offer else 0.0) + (ret_price if ret_offer else 0.0)

    airline = None
    legs_out, legs_ret = [], []
    stops_out, stops_ret = None, None
    dur_out, dur_ret = None, None

    if out_offer:
        slc = (out_offer.get("slices") or [None])[0] or {}
        legs_out, stops_out, dur_out = _legs_from_slice(slc)
        if legs_out:
            airline = legs_out[0].carrier or airline

    if ret_offer:
        slc = (ret_offer.get("slices") or [None])[0] or {}
        legs_ret, stops_ret, dur_ret = _legs_from_slice(slc)
        if not airline and legs_ret:
            airline = legs_ret[0].carrier

    is_direct_out = (stops_out == 0) if stops_out is not None else None
    is_direct_ret = (stops_ret == 0) if stops_ret is not None else None

    def _stop_text(stops):
        if stops is None: return "unknown"
        if stops == 0: return "direct"
        if stops == 1: return "1 stop"
        return f"{stops} stops"

    stop_summary = f"{_stop_text(stops_out)}/{_stop_text(stops_ret)}"
    summary = f"{origin}↔{destination} ({airline or 'Mixed'}, {stop_summary})"

    return FlightOption(
        summary=summary,
        price_total=total,
        price_currency=currency,
        airline=airline,
        deep_link=None,
        origin_iata=origin,
        destination_iata=destination,
        outbound_price=out_price if out_offer else None,
        return_price=ret_price if ret_offer else None,
        legs_outbound=legs_out,
        legs_return=legs_ret,
        stops_outbound=stops_out,
        stops_return=stops_ret,
        duration_outbound_iso=dur_out,
        duration_return_iso=dur_ret,
        is_direct_outbound=is_direct_out,
        is_direct_return=is_direct_ret,
    )
