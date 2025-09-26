from typing import List, Optional
from schemas import FlightOption
from providers.amadeus import search_flights_amadeus
from providers.duffel import search_flights_duffel

async def get_flight_options(origin_iata: str, dest_iata: str, depart_date: str, return_date: Optional[str], adults: int = 1) -> List[FlightOption]:
    options: List[FlightOption] = []
    # Fetch from Amadeus API
    try:
        data = await search_flights_amadeus(origin_iata, dest_iata, depart_date, return_date, adults)
        for offer in data.get("data", [])[:5]:
            price = offer.get("price", {})
            total = float(price.get("total", 0))
            currency = price.get("currency", "USD")
            itineraries = offer.get("itineraries", [])
            summary = "; ".join([f"{seg['segments'][0]['departure']['iataCode']}→{seg['segments'][-1]['arrival']['iataCode']} ({len(seg['segments'])-1} stops)" for seg in itineraries])
            options.append(FlightOption(provider="amadeus", summary=summary, price_currency=currency, price_total=total))
    except Exception as e:
        print(f"Error fetching flight options from Amadeus: {e}")
    
    # Fallback to Duffel API
    try:
        d = await search_flights_duffel(origin_iata, dest_iata, depart_date, return_date, adults)
        if d and d.get("data"):
            for off in d["data"][:5]:
                total = float(off["total_amount"]) if off.get("total_amount") else 0.0
                currency = off.get("total_currency") or "USD"
                summary = off.get("owner", {}).get("name", "Duffel offer")
                options.append(FlightOption(provider="duffel", summary=summary, price_currency=currency, price_total=total))
    except Exception as e:
        print(f"Error fetching flight options from Duffel: {e}")
    
    # Sort by price
    options.sort(key=lambda x: x.price_total or float("inf"))
    return options[:5]
