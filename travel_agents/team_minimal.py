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
from schemas import PlannerPayload, PackageOption, PlanResponse
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))
from flights_agent import get_flight_options
from accommodation_agent import get_hotel_options  # Accommodation agent

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

def get_geolocation(country_or_city: str) -> str:
    # Use OpenCage Geocoder to get country and city info from free text input
    url = f"https://api.opencagedata.com/geocode/v1/json?q={country_or_city}&key={GEOCODE_API_KEY}"
    response = requests.get(url)
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

async def plan_trip(user_prompt: str):
    missing = []
    country, start_date, num_days = extract_trip_details(user_prompt)

    # If dates or number of days are missing, ask interactively
    if not start_date:
        start_date = input(f"Enter start date (YYYY-MM-DD, default today {date.today()}): ").strip() or str(date.today())

    if not num_days:
        num_days = int(input("Enter the number of days for your trip: ").strip())

    # Calculate the end date based on start date and number of days
    end_date = (date.fromisoformat(start_date) + timedelta(days=num_days)).isoformat()

    # Get the city code for the country
    city_code = await find_city_code(country)  # Example: convert 'Sri Lanka' to 'CMB'

    origin_iata = "DEL"  # Default origin (India)

    # Get flight options if no missing data
    flights = await get_flight_options(
        origin_iata, city_code, start_date, end_date, 1
    ) if not missing else []

    # Get hotel options if no missing data
    hotels = await get_hotel_options(
        city_code, start_date, end_date, 1
    ) if not missing else []

    packages = []

    # Generate combo packages from the first 3 flights and hotels
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

    packages = sorted(packages, key=lambda p: p.est_total)[:4]
    return PlanResponse(query={"city": country}, packages=packages, missing=missing)

# ---------------------------
# Main Entry Point (Async)
# ---------------------------

async def main():
    # Setup Gemini model client
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

    # --------------------------
    # Define Your Agents
    # --------------------------
    planner = AssistantAgent(
        name="planner",
        description="Plans itineraries step-by-step with constraints.",
        system_message="Plan clearly in numbered steps. End with DONE.",
        model_client=model_client,
    )

    you = UserProxyAgent(name="you")

    # ---------------------------
    # RoundRobinGroupChat for Agent Collaboration
    # ---------------------------
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
    print("\n================= ORIGINAL TEAM RESULT =================\n")
    print(result_plan.messages[-1].content)

    # ---------------------------
    # Main trip planning logic
    # ---------------------------
    print("\nEnter trip details for Accommodation & Travel Agent:\n")
    user_prompt = input("Enter prompt: ").strip()

    # Running the agents to get packages (flights + hotels)
    resp = await plan_trip(user_prompt)

    # Display the result
    print("\n================= TOP PACKAGE OPTIONS =================\n")
    for i, pkg in enumerate(resp.packages, 1):
        print(f"\n{i}. {pkg.title}")
        print(f"Flights: {pkg.flights.provider} | {pkg.flights.summary} | {pkg.flights.price_currency} {pkg.flights.price_total}")
        print(f"Hotel:   {pkg.hotel.provider} | {pkg.hotel.name} | {pkg.hotel.price_currency} {pkg.hotel.price_total}")
        print(f"Total: {pkg.est_total_currency} {pkg.est_total}")

if __name__ == "__main__":
    asyncio.run(main())
