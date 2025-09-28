from dotenv import load_dotenv 
load_dotenv()

import os, sys, asyncio, json, re
from datetime import datetime
from rich import print as rprint

from schemas import (
    TripQuery, FlightSearchInput, HotelSearchInput,
    FlightSearchResult, HotelSearchResult, FlightOption, HotelOption
)
from nlp import parse_trip_free_text
from combo import make_combos

# Agents (kept for structure)
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

from providers.amadeus_api import city_search, hotel_offers, normalize_hotels, city_country_for_code
from providers.duffel_api import search_one_way_topn, normalize_roundtrip_pair
# Booking.com (RapidAPI) fallback
from providers.booking_api import (
    find_city_dest_id,
    booking_hotel_search_city,
    normalize_booking_hotels,
)

# ---------- LLM client (Gemini via OpenAI-compatible) ----------
model_client = OpenAIChatCompletionClient(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    model_info={"function_calling": True, "vision": False, "json_output": False, "family": "gemini"},
)

# ---------- Country -> hub-city fallback ----------
COUNTRY_TO_CITY = {
    "japan": "Tokyo", "india": "Delhi", "sri lanka": "Colombo", "uae": "Dubai",
    "united arab emirates": "Dubai", "thailand": "Bangkok", "singapore": "Singapore",
    "malaysia": "Kuala Lumpur", "indonesia": "Jakarta", "vietnam": "Ho Chi Minh City",
    "france": "Paris", "italy": "Rome", "spain": "Barcelona", "germany": "Berlin",
    "uk": "London", "united kingdom": "London", "netherlands": "Amsterdam",
    "usa": "New York", "united states": "New York", "canada": "Toronto",
    "mexico": "Mexico City", "brazil": "São Paulo", "australia": "Sydney",
    "new zealand": "Auckland",
}

# Additional origin mappings straight to city codes (helps sandbox)
ORIGIN_TEXT_TO_CITY_CODE = {
    "canada": "YTO", "toronto": "YTO", "montreal": "YMQ", "vancouver": "YVR",
    "colombo": "CMB", "sri lanka": "CMB", "new york": "NYC", "london": "LON", "paris": "PAR",
}

def resolve_destination_city(text_place: str) -> str:
    t = (text_place or "").strip()
    if not t:
        return "Colombo"
    key = t.lower()
    if key in COUNTRY_TO_CITY:
        return COUNTRY_TO_CITY[key]
    return t  # assume city name

# ---------- Robust "from X to Y" parser ----------
def parse_from_to(text: str) -> tuple[str | None, str | None]:
    text_l = text.lower().strip()
    m = re.search(r'\b(?:from|leaving from|start in)\s+([a-z\s,]+?)\s+(?:to|->)\s+([a-z\s,]+)\b', text_l, re.I)
    if m:
        return m.group(1).strip(" ,"), m.group(2).strip(" ,")
    m2 = re.search(r'\b([a-z\s,]+?)\s+(?:to|->)\s+([a-z\s,]+)\b', text_l, re.I)
    if m2:
        return m2.group(1).strip(" ,"), m2.group(2).strip(" ,")
    return None, None

def parse_origin_free_text(text: str) -> str:
    o, _ = parse_from_to(text)
    if o:
        return o
    m = re.search(r'(?:from|start in|leaving from)\s+([A-Za-z\s,]+?)(?:$|[.!?,])', text, re.I)
    if m:
        return m.group(1).strip(" ,")
    return ""

def resolve_iata_city_code(free_text_city: str, fallback: str = "CMB") -> str:
    if not free_text_city:
        return fallback
    key = free_text_city.strip().lower()
    if key in ORIGIN_TEXT_TO_CITY_CODE:
        return ORIGIN_TEXT_TO_CITY_CODE[key]
    code = city_search(free_text_city)
    if code:
        return code
    hub = resolve_destination_city(free_text_city)
    code2 = city_search(hub)
    return code2 or fallback

# ---------- Pretty printing helpers with emojis ----------
def _friendly_time(iso_str: str | None) -> str:
    if not iso_str:
        return "time unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %H:%M")
    except Exception:
        return iso_str.replace("T", " ")

def _friendly_dur(iso_dur: str | None) -> str:
    if not iso_dur: return "?"
    # supports PT#H#M and PnDT... patterns; we simplify for display
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", iso_dur.replace("PT", "T"))
    if not m:
        m2 = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso_dur)
        if not m2: return iso_dur
        h = int(m2.group(1) or 0); mn = int(m2.group(2) or 0)
        return (f"{h}h " if h else "") + (f"{mn}m" if mn else "") or "0m"
    d = int(m.group(1) or 0); h = int(m.group(2) or 0); mn = int(m.group(3) or 0)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if mn: parts.append(f"{mn}m")
    return " ".join(parts) if parts else "0m"

def _stop_text(stops: int | None) -> str:
    if stops is None: return "stops unknown"
    if stops == 0: return "Direct flight"
    if stops == 1: return "1 stop"
    return f"{stops} stops"

def _disp(code: str | None) -> str:
    return city_country_for_code(code or "") if code else "UNKNOWN"

def _legs_natural(legs):
    lines = []
    for lg in legs or []:
        if isinstance(lg, dict):
            carrier = lg.get("carrier") or "Flight"
            flight_number = lg.get("flight_number")
            origin = _disp(lg.get("origin"))
            destination = _disp(lg.get("destination"))
            departure_time = lg.get("departure_time")
            duration_iso = lg.get("duration_iso")
            cabin_class = lg.get("cabin_class")
        else:
            carrier = getattr(lg, "carrier", None) or "Flight"
            flight_number = getattr(lg, "flight_number", None)
            origin = _disp(getattr(lg, "origin", None))
            destination = _disp(getattr(lg, "destination", None))
            departure_time = getattr(lg, "departure_time", None)
            duration_iso = getattr(lg, "duration_iso", None)
            cabin_class = getattr(lg, "cabin_class", None)

        fn = f" {flight_number}" if flight_number else ""
        dep = _friendly_time(departure_time)
        dur = _friendly_dur(duration_iso)
        cabin = f", {str(cabin_class).capitalize()}" if cabin_class else ""
        lines.append(f"    ✈️ {carrier}{fn} — {origin} → {destination} on {dep} ({dur}{cabin})")
    return "\n".join(lines)

def print_pretty(final_dict: dict):
    dest = final_dict.get("destination", "—")
    window = final_dict.get("date_window", "—")
    combos = final_dict.get("combos", []) or []

    print("\n==============================")
    print(f"🌍 Trip plan: {dest}")
    print(f"📅 Dates: {window}")
    print("==============================\n")

    if not combos:
        print("No packages found.")
        return

    for i, c in enumerate(combos, 1):
        title = c.get("title", f"Package {i}")
        flight = c.get("flight", {}) or {}
        hotel  = c.get("hotel", {}) or {}
        reasons = c.get("reasons", {}) or {}
        total_usd = c.get("est_total_usd", None)

        # Friendly route line using origin/destination IATA
        ori = _disp(flight.get("origin_iata"))
        dst = _disp(flight.get("destination_iata"))
        airline = flight.get("airline") or "Airline"
        so = flight.get("stops_outbound"); sr = flight.get("stops_return")
        stop_summary = f"{_stop_text(so).lower().replace(' flight','')}/{_stop_text(sr).lower().replace(' flight','')}"
        fsum = f"{ori} ↔ {dst} ({airline}, {stop_summary})"

        fccy = flight.get("price_currency", "USD")
        fprice = flight.get("price_total", None)
        out_p = flight.get("outbound_price", None)
        ret_p = flight.get("return_price", None)
        d_out = _friendly_dur(flight.get("duration_outbound_iso"))
        d_ret = _friendly_dur(flight.get("duration_return_iso"))

        hname = hotel.get("name", "Hotel")
        hstars = hotel.get("stars", None)
        hccy = hotel.get("price_currency", "USD")
        hprice = hotel.get("price_total", None)
        hhood = hotel.get("neighborhood", None)

        print(f"### ✨ Package {i}: {title}\n")

        print("✈️ Flight")
        print(f"  • {fsum}")
        if out_p is not None or ret_p is not None:
            op = f"${out_p:.2f} {fccy}" if isinstance(out_p,(int,float)) else "n/a"
            rp = f"${ret_p:.2f} {fccy}" if isinstance(ret_p,(int,float)) else "n/a"
            print(f"  • Outbound: {op} — about {d_out}")
            print(f"  • Return:   {rp} — about {d_ret}")
        if isinstance(fprice,(int,float)):
            print(f"  • Round-trip total: ${fprice:.2f} {fccy}")

        legs_out = _legs_natural(flight.get("legs_outbound"))
        legs_ret = _legs_natural(flight.get("legs_return"))
        if legs_out:
            print("  • Outbound details:")
            print(legs_out)
        if legs_ret:
            print("  • Return details:")
            print(legs_ret)

        print("\n🏨 Hotel")
        star_txt = f" {'⭐'*hstars}" if hstars else ""
        hood_txt = f" · {hhood}" if hhood else ""
        print(f"  • {hname}{star_txt}{hood_txt}")
        if isinstance(hprice,(int,float)):
            print(f"  • Stay price: ${hprice:.2f} {hccy}")

        if isinstance(total_usd,(int,float)):
            print(f"\n💰 Total package estimate: ${total_usd:.2f} USD")

        # Reasons (varied in combo.py)
        why = reasons.get("why_together")
        pros = reasons.get("pros") or []
        cons = reasons.get("cons") or []
        if why:
            print(f"\nℹ️ Why this package: {why}")
        if pros:
            print("✅ Pros:")
            for p in pros:
                print(f"   + {p}")
        if cons:
            print("⚠️ Consider:")
            for n in cons:
                print(f"   - {n}")
        print("\n--------------------------------\n")

# ---------- Tool Wrapper Functions ----------
def tool_resolve_locations(user_query: str) -> dict:
    """Tool to resolve origin/destination from user query"""
    try:
        dest, country, sdate, edate, nights, adults = parse_trip_free_text(user_query)
        
        # Use from/to if present
        orig_inline, dest_inline = parse_from_to(user_query)
        if dest_inline:
            dest = dest_inline
        
        origin_text = parse_origin_free_text(user_query)
        if not origin_text:
            origin_text = "Colombo Sri Lanka"
            
        # Resolve city names → IATA
        city_name = resolve_destination_city(dest)
        dest_city_code = resolve_iata_city_code(city_name, fallback="PAR")
        origin_city_code = resolve_iata_city_code(origin_text, fallback="CMB")
        
        return {
            "destination": dest,
            "city_name": city_name,
            "dest_city_code": dest_city_code,
            "origin_city_code": origin_city_code,
            "start_date": sdate,
            "end_date": edate,
            "adults": adults,
            "nights": nights
        }
    except Exception as e:
        return {"error": f"Failed to resolve locations: {e}"}

def tool_search_flights(origin_code: str, dest_code: str, start_date: str, end_date: str, adults: int) -> dict:
    """Tool to search for flights"""
    try:
        # ---- Flights: top-3 each way via Duffel, paired by index ----
        out = search_one_way_topn(origin_code, dest_code, start_date or "", adults, n=3)
        ret = search_one_way_topn(dest_code, origin_code, end_date or "", adults, n=3) if end_date else {"offers": [], "debug": "No end_date provided"}

        out_offers = out.get("offers") or []
        ret_offers = ret.get("offers") or []

        flight_options: list[FlightOption] = []
        for i in range(min(3, len(out_offers or []), len(ret_offers or []))):
            fopt = normalize_roundtrip_pair(origin_code, dest_code, out_offers[i], ret_offers[i])
            flight_options.append(fopt)
        if not flight_options and (out_offers or ret_offers):
            top = out_offers or ret_offers
            for i in range(min(3, len(top))):
                fopt = normalize_roundtrip_pair(origin_code, dest_code, top[i] if out_offers else None, None if out_offers else top[i])
                flight_options.append(fopt)
        if not flight_options:
            from schemas import FlightLeg
            flight_options = [
                FlightOption(
                    summary=f"{origin_code}↔{dest_code} (MockAir, direct/direct)",
                    price_total=500.0, price_currency="USD", airline="MockAir",
                    origin_iata=origin_code, destination_iata=dest_code,
                    outbound_price=250.0, return_price=250.0,
                    legs_outbound=[FlightLeg(carrier="MockAir", origin=origin_code, destination=dest_code, duration_iso="PT5H")],
                    legs_return=[FlightLeg(carrier="MockAir", origin=dest_code, destination=origin_code, duration_iso="PT5H")],
                    stops_outbound=0, stops_return=0,
                    duration_outbound_iso="PT5H", duration_return_iso="PT5H",
                    is_direct_outbound=True, is_direct_return=True
                )
            ]

        flight_result = FlightSearchResult(
            source="duffel" if (out_offers or ret_offers) else "mock",
            options=flight_options,
            debug="; ".join([d for d in [out.get('debug'), ret.get('debug')] if d]) or None
        )
        
        return {"flights": [f.model_dump() for f in flight_result.options], "debug": flight_result.debug}
    except Exception as e:
        return {"error": f"Flight search failed: {e}"}

def tool_search_hotels(dest_code: str, city_name: str, start_date: str, end_date: str, adults: int) -> dict:
    """Tool to search for hotels"""
    try:
        # ---- Hotels: Amadeus first, then Booking.com fallback ----
        raw_hotels = hotel_offers(dest_code, start_date, end_date, adults)
        hotels = normalize_hotels(raw_hotels)

        booking_dbg = None
        if not hotels:
            try:
                dest_id = find_city_dest_id(city_name)  # Booking.com uses dest_id (not IATA)
                if dest_id and start_date and end_date:
                    b_raw = booking_hotel_search_city(
                        dest_id=dest_id,
                        checkin=start_date,
                        checkout=end_date,
                        adults=adults,
                        currency="USD",
                        locale="en-gb",
                        order_by="price"
                    )
                    hotels = normalize_booking_hotels(b_raw)
                    booking_dbg = b_raw.get("error")
                else:
                    booking_dbg = "Missing dest_id or dates for Booking.com fallback"
            except Exception as booking_error:
                booking_dbg = f"Booking.com API error: {booking_error}"

        hsrc = "amadeus" if (raw_hotels.get("data") if isinstance(raw_hotels, dict) else None) else ("booking" if hotels else "mock")
        hdbg = None
        if not hotels:
            hdbg = f"No hotels from Amadeus or Booking for {city_name} ({start_date}..{end_date})."
            hotels = [
                {"name": "Test Property — Budget", "stars": 2, "neighborhood": "Central", "price_total": 55.0, "price_currency": "EUR", "deep_link": None},
                {"name": "Test Property — Midscale", "stars": 3, "neighborhood": "Central", "price_total": 95.0, "price_currency": "EUR", "deep_link": None},
                {"name": "Test Property — Boutique", "stars": 4, "neighborhood": "Central", "price_total": 145.0, "price_currency": "EUR", "deep_link": None},
            ]

        return {"hotels": hotels, "debug": booking_dbg or hdbg}
    except Exception as e:
        return {"error": f"Hotel search failed: {e}"}

def tool_make_combos(destination: str, date_window: str, flights_data: list, hotels_data: list) -> dict:
    """Tool to combine flights and hotels into packages"""
    try:
        flights = [FlightOption(**f) for f in flights_data]
        hotels = [HotelOption(**h) for h in hotels_data]
        
        final = make_combos(destination=destination, date_window=date_window, flights=flights, hotels=hotels)
        return final.model_dump()
    except Exception as e:
        return {"error": f"Package combination failed: {e}"}

def tool_print_results(combos_data: dict) -> str:
    """Tool to format and print final results"""
    try:
        print_pretty(combos_data)
        return "Results displayed successfully"
    except Exception as e:
        return f"Error displaying results: {e}"

# ---------- Agents with Tools ----------
flight_agent = AssistantAgent(
    name="flight_agent",
    description="Finds flight options using Duffel API",
    system_message="""You are the Flight Search Agent. When asked to search for flights, use the tool_search_flights function with the provided parameters (origin_code, dest_code, start_date, end_date, adults). Return the flight results to the orchestrator. Always be helpful and provide clear information about the flights found.""",
    model_client=model_client,
    tools=[tool_search_flights]
)

stay_agent = AssistantAgent(
    name="stay_agent",
    description="Finds hotel options using Amadeus and Booking APIs",
    system_message="""You are the Hotel Search Agent. When asked to search for hotels, use the tool_search_hotels function with the provided parameters (dest_code, city_name, start_date, end_date, adults). Return the hotel results to the orchestrator. Always be helpful and provide clear information about the accommodations found.""",
    model_client=model_client,
    tools=[tool_search_hotels]
)

orchestrator = AssistantAgent(
    name="orchestrator",
    description="Coordinates travel planning and combines results",
    system_message="""You are the Travel Planning Orchestrator. Your role is to:
1. Parse user travel requests using tool_resolve_locations
2. Ask flight_agent to search flights with the resolved parameters
3. Ask stay_agent to search hotels with the resolved parameters  
4. Use tool_make_combos to combine the results into travel packages
5. Use tool_print_results to display the final packages
6. End your final message with "DONE" to complete the process

Always coordinate politely with other agents and provide clear instructions.""",
    model_client=model_client,
    tools=[tool_resolve_locations, tool_make_combos, tool_print_results]
)

user = UserProxyAgent(name="you")
team = RoundRobinGroupChat(
    participants=[user, orchestrator, flight_agent, stay_agent],
    termination_condition=TextMentionTermination("DONE"),
    max_turns=12,
)

# ---------- Terminal prompts ----------
def prompt_user() -> TripQuery:
    print("\n== Trip Planner ==\n")
    try:
        where = input("Where do you want to plan or go for trip?\n> ").strip()
    except EOFError:
        where = "Paris in November for 4 nights, 2 adults"
    if not where:
        where = "Paris in November for 4 nights, 2 adults"

    dest, country, sdate, edate, nights, adults = parse_trip_free_text(where)

    # Use from/to if present
    orig_inline, dest_inline = parse_from_to(where)
    if dest_inline:
        dest = dest_inline

    origin_text = parse_origin_free_text(where)

    if not sdate or not edate:
        print("\nYou didn’t give exact dates. Optional: press Enter to auto-pick.")
        sd_in = input("Start date (YYYY-MM-DD): ").strip()
        ed_in = input("End date   (YYYY-MM-DD): ").strip()
        sdate = sd_in or sdate
        edate = ed_in or edate

    if not origin_text:
        try:
            origin_text = input("\nWhere are you starting from? (free text, e.g., 'Colombo Sri Lanka')\n> ").strip()
        except EOFError:
            origin_text = "Colombo Sri Lanka"

    return TripQuery(
        raw_text=where, destination=dest, country=country,
        start_date=sdate, end_date=edate, nights=nights, adults=adults,
        origin_text=origin_text or None
    )

async def main():
    """Main function now using multi-agent conversation"""
    try:
        q = prompt_user()

        # Create the initial message for the team
        initial_message = f"""Plan a trip with these details:
        
User Query: {q.raw_text}
Destination: {q.destination}
Start Date: {q.start_date or 'TBD'}
End Date: {q.end_date or 'TBD'}
Adults: {q.adults}
Origin: {q.origin_text or 'Not specified'}

Please coordinate to find flights, hotels, and create travel packages."""

        print(f"\n🎯 Starting multi-agent trip planning...")
        print(f"📋 Request: {initial_message}")
        
        # Kick off the conversation by letting the user speak first
        await team.a_send(message=initial_message, sender=user)
        # Then run the group chat loop until termination condition is met
        result = await team.run()
        
        print("\n✅ Multi-agent travel planning completed!")
        
    except Exception as e:
        print(f"\n❌ Error in agent conversation: {e}")
        rprint(f"\n[bold red]Agent Error:[/bold red] {e}")
        
        # Fallback to show that system still works
        print("\n🔄 Falling back to direct tool processing...")
        q = prompt_user() if 'q' not in locals() else q
        
        # Use tools directly as fallback
        locations = tool_resolve_locations(q.raw_text)
        if "error" not in locations:
            print(f"✅ Locations resolved: {locations['origin_city_code']} → {locations['dest_city_code']}")
            
            flights = tool_search_flights(
                locations["origin_city_code"],
                locations["dest_city_code"], 
                locations["start_date"],
                locations["end_date"],
                locations["adults"]
            )
            
            if "error" not in flights:
                print(f"✅ Found {len(flights['flights'])} flight options")
                
                hotels = tool_search_hotels(
                    locations["dest_city_code"],
                    locations["city_name"],
                    locations["start_date"], 
                    locations["end_date"],
                    locations["adults"]
                )
                
                if "error" not in hotels:
                    print(f"✅ Found {len(hotels['hotels'])} hotel options")
                    
                    # Prefer user's provided dates in fallback output window
                    date_window = f"{q.start_date or locations['start_date']} to {q.end_date or locations['end_date']}"
                    combos = tool_make_combos(
                        locations["city_name"],
                        date_window,
                        flights["flights"],
                        hotels["hotels"]
                    )
                    
                    if "error" not in combos:
                        print("\n✅ Packages created successfully!")
                        tool_print_results(combos)
                    else:
                        print(f"❌ Package creation failed: {combos['error']}")
                else:
                    print(f"❌ Hotel search failed: {hotels['error']}")
            else:
                print(f"❌ Flight search failed: {flights['error']}")
        else:
            print(f"❌ Location resolution failed: {locations['error']}")

if __name__ == "__main__":
    asyncio.run(main())
