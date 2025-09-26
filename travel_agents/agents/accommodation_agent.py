from typing import List
from schemas import HotelOption
from providers.amadeus import search_hotels_amadeus

async def get_hotel_options(city_code: str, check_in: str, check_out: str, adults: int = 1) -> List[HotelOption]:
    options: List[HotelOption] = []
    try:
        data = await search_hotels_amadeus(city_code, check_in, check_out, adults)
        for item in data.get("data", [])[:10]:
            hotel = item.get("hotel", {})
            offers = item.get("offers", [])
            if not offers:
                continue
            offer = offers[0]
            price = offer.get("price", {})
            total = float(price.get("total", 0))
            currency = price.get("currency", "LKR")
            options.append(HotelOption(
                provider="amadeus",
                name=hotel.get("name", "Hotel"),
                city=hotel.get("address", {}).get("cityName", ""),
                price_currency=currency,
                price_total=total,
                check_in=offer.get("checkInDate"),
                check_out=offer.get("checkOutDate"),
                address=hotel.get("address", {}).get("lines", [])[0] if hotel.get("address") else None,
                deep_link=None
            ))
    except Exception as e:
        print(f"Error fetching hotel options: {e}")
    
    options.sort(key=lambda x: x.price_total)
    return options[:5]
