import os, sys, asyncio, json
from datetime import date, timedelta
from dotenv import load_dotenv
import requests
import re

# Ensure we can import modules in this folder
sys.path.append(os.path.dirname(__file__))

# --- AutoGen (AgentChat) ---
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

# --- Gemini via OpenAI-compatible client ---
from autogen_ext.models.openai import OpenAIChatCompletionClient

# --- Your local agent logic (modules are in the SAME folder) ---
from schemas import PlannerPayload, PackageOption, PlanResponse, TripQuery
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))
from agents.flights_agent import get_flight_options
from agents.accommodation_agent import get_hotel_options  # Accommodation agent

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
GEOCODE_API_KEY = os.getenv("GEOCODE_API_KEY")  # Your OpenCage Geocoder API key

# ---------------------------
# Tool wrappers for AutoGen
# ---------------------------
def tool_score_payload(payload_json: str) -> str:
    """
    Input: JSON string matching PlannerPayload schema.
    Output: Placeholder for additional logic if needed.
    """
    return json.dumps({"status": "scam_check_done"})

def tool_merge_and_explain(planner_json: str, checks_json: str) -> str:
    """
    Input: Planner JSON (trip request) and ScamWatcher JSON (fraud check)
    Output: Merges them (we don't need this step right now).
    """
    return planner_json

# ---------------------------
# Extract details from the user prompt using Geocoding API
# ---------------------------

def get_geolocation(country_or_city: str) -> tuple:
    """Get country and city from location string using OpenCage Geocoder API"""
    if not GEOCODE_API_KEY:
        print("Warning: GEOCODE_API_KEY not found. Using fallback mapping.")
        return None, None
        
    # Use OpenCage Geocoder to get country and city info from free text input
    url = f"https://api.opencagedata.com/geocode/v1/json?q={country_or_city}&key={GEOCODE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract country and city
        if data['results']:
            country = None
            city = None
            for result in data['results']:
                if 'components' in result:
                    if 'country' in result['components']:
                        country = result['components']['country']
                    if 'city' in result['components']:
                        city = result['components']['city']
                if country:  # Stop at the first valid result
                    break
            return country, city
    except Exception as e:
        print(f"Error fetching geolocation: {e}")
    return None, None

def extract_trip_details(prompt: str):
    # Extracts country or city from the user prompt
    country_or_city_match = re.search(r"([A-Za-z\s]+)", prompt)  # Simple regex to capture country/city
    country_or_city = country_or_city_match.group(1) if country_or_city_match else "Sri Lanka"

    # Call geocoding API to get the country and city
    country, city = get_geolocation(country_or_city)

    # Extract the number of days
    days_match = re.search(r"(\d+)\s*days?", prompt, re.IGNORECASE)
    num_days = int(days_match.group(1)) if days_match else None

    # Extract start date
    date_match = re.findall(r"\d{4}-\d{2}-\d{2}", prompt)
    start_date = date_match[0] if date_match else None

    return country, start_date, num_days

# ---------------------------
# Plan trip logic with agents
# ---------------------------

def find_city_code(country: str) -> str:
    """Map countries to city codes with fallback to Amadeus API"""
    # A mock function to map countries to city codes.
    # You can extend this with more countries and their codes.
    
    country_mapping = {
        "Sri Lanka": "CMB",  # Colombo, Sri Lanka
        "Mexico": "MEX",     # Mexico City
        "India": "DEL",      # Delhi, India
        "USA": "NYC",        # New York, USA
        "Japan": "HND",      # Tokyo, Japan
        "Australia": "SYD",  # Sydney, Australia
        "United States": "NYC",
        "United Kingdom": "LHR",
        "France": "CDG",
        "Germany": "FRA",
        "Italy": "FCO",
        "Spain": "MAD",
        "Thailand": "BKK",
        "Singapore": "SIN",
        "Malaysia": "KUL",
        "Indonesia": "CGK",
        "Philippines": "MNL",
        "Vietnam": "SGN",
        "South Korea": "ICN",
        "China": "PEK",
        "Canada": "YYZ",
        "Brazil": "GRU",
        "Argentina": "EZE",
        "Chile": "SCL",
        "Peru": "LIM",
        "Colombia": "BOG",
        "South Africa": "JNB",
        "Egypt": "CAI",
        "Morocco": "CMN",
        "Turkey": "IST",
        "Russia": "SVO",
        "Poland": "WAW",
        "Czech Republic": "PRG",
        "Hungary": "BUD",
        "Greece": "ATH",
        "Portugal": "LIS",
        "Netherlands": "AMS",
        "Belgium": "BRU",
        "Switzerland": "ZUR",
        "Austria": "VIE",
        "Sweden": "ARN",
        "Norway": "OSL",
        "Denmark": "CPH",
        "Finland": "HEL",
        "Ireland": "DUB",
        "New Zealand": "AKL",
        "Israel": "TLV",
        "United Arab Emirates": "DXB",
        "Saudi Arabia": "RUH",
        "Qatar": "DOH",
        "Kuwait": "KWI",
        "Bahrain": "BAH",
        "Oman": "MCT",
        "Jordan": "AMM",
        "Lebanon": "BEY",
        "Cyprus": "LCA",
        "Malta": "MLA",
        "Iceland": "KEF",
        "Luxembourg": "LUX",
        "Monaco": "MCO",
        "Liechtenstein": "ZUR",  # Use Zurich as closest
        "San Marino": "RMI",     # Use Rimini as closest
        "Vatican City": "FCO",   # Use Rome as closest
        "Andorra": "BCN",        # Use Barcelona as closest
    }

    # Check if country is in mapping
    if country in country_mapping:
        return country_mapping[country]
    
    # If not found in mapping, try to get from geocoding API
    country_from_api, city_from_api = get_geolocation(country)
    if country_from_api and country_from_api in country_mapping:
        return country_mapping[country_from_api]

    # Default to Colombo (CMB) if the country is not found
    print(f"Warning: Country '{country}' not found in mapping. Using Colombo (CMB) as default.")
    return "CMB"

async def plan_trip(user_prompt: str):
    """Plan a trip based on user prompt with error handling"""
    missing = []
    try:
        country, start_date, num_days = extract_trip_details(user_prompt)
        
        print(f"\n📍 Detected destination: {country}")
        
        # If dates or number of days are missing, ask interactively
        if not start_date:
            start_date = input(f"Enter start date (YYYY-MM-DD, default today {date.today()}): ").strip() or str(date.today())

        if not num_days:
            num_days_input = input("Enter the number of days for your trip: ").strip()
            if not num_days_input:
                num_days = 3  # Default to 3 days
            else:
                num_days = int(num_days_input)

        # Calculate the end date based on start date and number of days
        end_date = (date.fromisoformat(start_date) + timedelta(days=num_days)).isoformat()
        
        print(f"📅 Trip dates: {start_date} to {end_date} ({num_days} days)")

        # Get the city code for the country
        city_code = find_city_code(country)
        print(f"✈️  City code: {city_code}")

        origin_iata = "DEL"  # Default origin (India)
        print(f"🛫 Origin: {origin_iata}")

        # Get flight options if no missing data
        print("\n🔍 Searching for flights...")
        flights = await get_flight_options(
            origin_iata, city_code, start_date, end_date, 1
        ) if not missing else []

        # Get hotel options if no missing data
        print("🏨 Searching for hotels...")
        hotels = await get_hotel_options(
            city_code, start_date, end_date, 1
        ) if not missing else []

        packages = []

        # Generate combo packages from the first 3 flights and hotels
        if flights and hotels:
            print(f"📦 Creating packages from {len(flights)} flights and {len(hotels)} hotels...")
            for f in flights[:3]:
                for h in hotels[:3]:
                    est_total = f.price_total + h.price_total
                    title = f"Combo: {f.summary} + {h.name}"
                    packages.append(
                        PackageOption(
                            title=title,
                            flights=f,
                            hotel=h,
                            est_total_currency=f.price_currency,
                            est_total=round(est_total, 2),
                        )
                    )
        else:
            print("⚠️  No flights or hotels found. Creating individual options...")
            # If no packages can be created, return individual options
            if flights:
                for f in flights[:3]:
                    packages.append(
                        PackageOption(
                            title=f"Flight Only: {f.summary}",
                            flights=f,
                            hotel=HotelOption(
                                provider="N/A",
                                name="No hotel selected",
                                city=country,
                                price_currency="USD",
                                price_total=0,
                                check_in=start_date,
                                check_out=end_date
                            ),
                            est_total_currency=f.price_currency,
                            est_total=f.price_total,
                        )
                    )
            if hotels:
                for h in hotels[:3]:
                    packages.append(
                        PackageOption(
                            title=f"Hotel Only: {h.name}",
                            flights=FlightOption(
                                provider="N/A",
                                summary="No flight selected",
                                price_currency="USD",
                                price_total=0
                            ),
                            hotel=h,
                            est_total_currency=h.price_currency,
                            est_total=h.price_total,
                        )
                    )

        packages = sorted(packages, key=lambda p: p.est_total)[:4]
        
        # Create proper TripQuery object
        trip_query = TripQuery(
            origin=origin_iata,
            destination=country,
            start_date=start_date,
            end_date=end_date,
            adults=1,
            notes=f"Trip to {country}"
        )
        
        return PlanResponse(query=trip_query, packages=packages, missing=missing)
        
    except Exception as e:
        print(f"❌ Error planning trip: {e}")
        # Return empty response with error info
        trip_query = TripQuery(
            origin="DEL",
            destination="Unknown",
            start_date=str(date.today()),
            end_date=str(date.today() + timedelta(days=1)),
            adults=1,
            notes=f"Error: {str(e)}"
        )
        return PlanResponse(query=trip_query, packages=[], missing=[f"Error: {str(e)}"])

# ---------------------------
# Main Entry Point (Async)
# ---------------------------

async def main():
    """Main entry point with improved user interface"""
    print("🌍 Welcome to Tourist Attraction AI - Your Personal Travel Assistant!")
    print("=" * 60)
    
    # Check for required API keys
    missing_keys = []
    if not api_key:
        missing_keys.append("GEMINI_API_KEY")
    if not GEOCODE_API_KEY:
        missing_keys.append("GEOCODE_API_KEY")
    if not os.getenv("AMADEUS_CLIENT_ID"):
        missing_keys.append("AMADEUS_CLIENT_ID")
    if not os.getenv("AMADEUS_CLIENT_SECRET"):
        missing_keys.append("AMADEUS_CLIENT_SECRET")
    
    if missing_keys:
        print(f"⚠️  Warning: Missing API keys: {', '.join(missing_keys)}")
        print("Some features may not work properly. Please check your .env file.")
        print()
    
    # Setup Gemini model client (only if API key is available)
    model_client = None
    if api_key:
        try:
            model_client = OpenAIChatCompletionClient(
                model="gemini-2.5-flash",
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                model_info={
                    "function_calling": True,
                    "vision": False,
                    "json_output": False,
                    "structured_output": False,  
                    "family": "gemini",
                },
            )
            print("✅ Gemini AI model connected successfully!")
        except Exception as e:
            print(f"❌ Error connecting to Gemini AI: {e}")
            print("Continuing without AI planning features...")
    else:
        print("⚠️  Gemini AI not available - continuing with basic features only")
    
    print()

    # --------------------------
    # AI Planning Demo (if available)
    # --------------------------
    if model_client:
        try:
            print("🤖 AI Planning Demo:")
            print("-" * 30)
            
            # Define Your Agents
            planner = AssistantAgent(
                name="planner",
                description="Plans itineraries step-by-step with constraints.",
                system_message="Plan clearly in numbered steps. End with DONE.",
                model_client=model_client,
            )

            you = UserProxyAgent(name="you")

            # RoundRobinGroupChat for Agent Collaboration
            team_plan = RoundRobinGroupChat(
                participants=[you, planner],
                termination_condition=TextMentionTermination("DONE"),
                max_turns=6,
            )

            # Sample task for planning
            task = (
                "Create a 1-day Kandy sightseeing plan under 5000 LKR for two students. "
                "Minimize transport cost, include timings, add 2 free/low-cost alternatives. "
                "End with DONE."
            )

            # Get the result from the agents working together
            result_plan = await team_plan.run(task=task)
            print("\n================= AI PLANNING RESULT =================\n")
            print(result_plan.messages[-1].content)
            print("\n" + "=" * 60)
        except Exception as e:
            print(f"❌ AI Planning demo failed: {e}")
            print("Continuing with travel booking features...")

    # ---------------------------
    # Main trip planning logic
    # ---------------------------
    print("\n✈️  Travel Booking Assistant")
    print("-" * 30)
    print("Enter your travel request in natural language.")
    print("Examples:")
    print("  • 'I want to visit Japan for 5 days'")
    print("  • 'Plan a trip to Thailand starting 2024-03-15 for 7 days'")
    print("  • 'Book flights and hotels for Sri Lanka'")
    print()
    
    while True:
        try:
            user_prompt = input("🌍 Enter your travel request (or 'quit' to exit): ").strip()
            
            if user_prompt.lower() in ['quit', 'exit', 'q']:
                print("👋 Thank you for using Tourist Attraction AI! Safe travels!")
                break
                
            if not user_prompt:
                print("Please enter a valid travel request.")
                continue

            print(f"\n🔍 Processing: {user_prompt}")
            print("-" * 40)

            # Running the agents to get packages (flights + hotels)
            resp = await plan_trip(user_prompt)

            # Display the result
            print("\n" + "=" * 60)
            print("🎯 TOP TRAVEL PACKAGES")
            print("=" * 60)
            
            if resp.packages:
                for i, pkg in enumerate(resp.packages, 1):
                    print(f"\n📦 Package #{i}: {pkg.title}")
                    print(f"   ✈️  Flight: {pkg.flights.provider} | {pkg.flights.summary}")
                    print(f"   💰 Flight Price: {pkg.flights.price_currency} {pkg.flights.price_total}")
                    print(f"   🏨 Hotel: {pkg.hotel.provider} | {pkg.hotel.name}")
                    print(f"   💰 Hotel Price: {pkg.hotel.price_currency} {pkg.hotel.price_total}")
                    print(f"   💵 Total Cost: {pkg.est_total_currency} {pkg.est_total}")
                    if pkg.hotel.address:
                        print(f"   📍 Address: {pkg.hotel.address}")
                    print("-" * 40)
            else:
                print("❌ No travel packages found.")
                if resp.missing:
                    print("Missing information:")
                    for item in resp.missing:
                        print(f"  • {item}")
            
            print(f"\n📋 Trip Details:")
            print(f"   🛫 From: {resp.query.origin}")
            print(f"   🛬 To: {resp.query.destination}")
            print(f"   📅 Dates: {resp.query.start_date} to {resp.query.end_date}")
            print(f"   👥 Travelers: {resp.query.adults}")
            
            print("\n" + "=" * 60)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Thanks for using Tourist Attraction AI!")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            print("Please try again with a different request.")
            continue

if __name__ == "__main__":
    asyncio.run(main())
