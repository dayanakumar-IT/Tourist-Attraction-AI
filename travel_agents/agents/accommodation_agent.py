from typing import List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from schemas import HotelOption
from providers.amadeus import search_hotels_amadeus

async def get_hotel_options(city_code: str, check_in: str, check_out: str, adults: int = 1) -> List[HotelOption]:
    """Get hotel options from Amadeus API with better error handling"""
    options: List[HotelOption] = []
    
    try:
        print(f"  🔍 Searching Amadeus for hotels in {city_code}")
        data = await search_hotels_amadeus(city_code, check_in, check_out, adults)
        
        if data and data.get("data"):
            for item in data.get("data", [])[:10]:
                try:
                    hotel = item.get("hotel", {})
                    offers = item.get("offers", [])
                    
                    if not offers:
                        continue
                        
                    offer = offers[0]
                    price = offer.get("price", {})
                    total = float(price.get("total", 0))
                    currency = price.get("currency", "LKR")
                    
                    # Extract hotel details
                    hotel_name = hotel.get("name", "Hotel")
                    address_info = hotel.get("address", {})
                    city_name = address_info.get("cityName", city_code)
                    address_lines = address_info.get("lines", [])
                    address = address_lines[0] if address_lines else None
                    
                    # Extract offer details
                    check_in_date = offer.get("checkInDate", check_in)
                    check_out_date = offer.get("checkOutDate", check_out)
                    
                    if total > 0:  # Only add valid offers
                        options.append(HotelOption(
                            provider="amadeus",
                            name=hotel_name,
                            city=city_name,
                            price_currency=currency,
                            price_total=total,
                            check_in=check_in_date,
                            check_out=check_out_date,
                            address=address,
                            deep_link=None
                        ))
                except Exception as e:
                    print(f"    ⚠️  Error processing hotel offer: {e}")
                    continue
        else:
            print(f"  ⚠️  No hotel data from Amadeus")
            
    except Exception as e:
        print(f"  ❌ Error fetching hotel options: {e}")
    
    # If no real options found, return empty list (no mock data)
    if not options:
        print(f"  ⚠️  No hotel options found from any provider")
        print(f"  💡 Please check your API credentials and try again")
    
    options.sort(key=lambda x: x.price_total)
    print(f"  ✅ Found {len(options)} hotel options")
    return options[:5]
