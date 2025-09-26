from typing import List, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from schemas import FlightOption
from providers.amadeus import search_flights_amadeus
from providers.duffel import search_flights_duffel

async def get_flight_options(origin_iata: str, dest_iata: str, depart_date: str, return_date: Optional[str], adults: int = 1) -> List[FlightOption]:
    """Get flight options from multiple providers with better error handling"""
    options: List[FlightOption] = []
    
    # Fetch from Amadeus API
    try:
        print(f"  🔍 Searching Amadeus for flights: {origin_iata} → {dest_iata}")
        data = await search_flights_amadeus(origin_iata, dest_iata, depart_date, return_date, adults)
        
        if data and data.get("data"):
            for offer in data.get("data", [])[:5]:
                try:
                    price = offer.get("price", {})
                    total = float(price.get("total", 0))
                    currency = price.get("currency", "USD")
                    itineraries = offer.get("itineraries", [])
                    
                    if itineraries:
                        summary_parts = []
                        for seg in itineraries:
                            segments = seg.get('segments', [])
                            if segments:
                                dep_code = segments[0]['departure']['iataCode']
                                arr_code = segments[-1]['arrival']['iataCode']
                                stops = len(segments) - 1
                                summary_parts.append(f"{dep_code}→{arr_code} ({stops} stops)")
                        summary = "; ".join(summary_parts) if summary_parts else "Flight available"
                    else:
                        summary = "Flight available"
                    
                    if total > 0:  # Only add valid offers
                        options.append(FlightOption(
                            provider="amadeus", 
                            summary=summary, 
                            price_currency=currency, 
                            price_total=total
                        ))
                except Exception as e:
                    print(f"    ⚠️  Error processing Amadeus offer: {e}")
                    continue
        else:
            print(f"  ⚠️  No flight data from Amadeus")
            
    except Exception as e:
        print(f"  ❌ Error fetching flight options from Amadeus: {e}")
    
    # Fallback to Duffel API
    try:
        print(f"  🔍 Searching Duffel for flights: {origin_iata} → {dest_iata}")
        d = await search_flights_duffel(origin_iata, dest_iata, depart_date, return_date, adults)
        
        if d and d.get("data"):
            for off in d["data"][:5]:
                try:
                    total = float(off["total_amount"]) if off.get("total_amount") else 0.0
                    currency = off.get("total_currency") or "USD"
                    summary = off.get("owner", {}).get("name", "Duffel offer")
                    
                    if total > 0:  # Only add valid offers
                        options.append(FlightOption(
                            provider="duffel", 
                            summary=summary, 
                            price_currency=currency, 
                            price_total=total
                        ))
                except Exception as e:
                    print(f"    ⚠️  Error processing Duffel offer: {e}")
                    continue
        else:
            print(f"  ⚠️  No flight data from Duffel")
            
    except Exception as e:
        print(f"  ❌ Error fetching flight options from Duffel: {e}")
    
    # If no real options found, return empty list (no mock data)
    if not options:
        print(f"  ⚠️  No flight options found from any provider")
        print(f"  💡 Please check your API credentials and try again")
    
    # Sort by price
    options.sort(key=lambda x: x.price_total or float("inf"))
    print(f"  ✅ Found {len(options)} flight options")
    return options[:5]
