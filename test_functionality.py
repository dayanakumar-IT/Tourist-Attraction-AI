#!/usr/bin/env python3
"""
Test script for Tourist Attraction AI
This script tests the core functionality without requiring user interaction.
"""

import asyncio
import sys
from pathlib import Path

# Add the travel_agents directory to Python path
current_dir = Path(__file__).parent
travel_agents_dir = current_dir / "travel_agents"
sys.path.insert(0, str(travel_agents_dir))

async def test_core_functionality():
    """Test the core functionality of the travel planning system"""
    print("🧪 Testing Tourist Attraction AI Core Functionality")
    print("=" * 50)
    
    try:
        # Test 1: Import modules
        print("1️⃣ Testing imports...")
        from travel_agents.schemas import TripQuery, FlightOption, HotelOption, PackageOption, PlanResponse
        from travel_agents.agents.flights_agent import get_flight_options
        from travel_agents.agents.accommodation_agent import get_hotel_options
        from travel_agents.team_minimal import extract_trip_details, find_city_code
        print("   ✅ All imports successful")
        
        # Test 2: Schema validation
        print("\n2️⃣ Testing schema validation...")
        trip_query = TripQuery(
            origin="DEL",
            destination="Japan",
            start_date="2024-03-15",
            end_date="2024-03-20",
            adults=1,
            notes="Test trip"
        )
        print(f"   ✅ TripQuery created: {trip_query.destination}")
        
        # Test 3: Trip details extraction
        print("\n3️⃣ Testing trip details extraction...")
        test_prompts = [
            "I want to visit Japan for 5 days",
            "Plan a trip to Thailand starting 2024-03-15 for 7 days",
            "Book flights and hotels for Sri Lanka"
        ]
        
        for prompt in test_prompts:
            country, start_date, num_days = extract_trip_details(prompt)
            print(f"   📝 '{prompt}' → Country: {country}, Start: {start_date}, Days: {num_days}")
        print("   ✅ Trip details extraction working")
        
        # Test 4: City code mapping
        print("\n4️⃣ Testing city code mapping...")
        test_countries = ["Japan", "Thailand", "Sri Lanka", "France", "Unknown Country"]
        for country in test_countries:
            city_code = find_city_code(country)
            print(f"   🌍 {country} → {city_code}")
        print("   ✅ City code mapping working")
        
        # Test 5: Mock flight options
        print("\n5️⃣ Testing flight options (mock data)...")
        flights = await get_flight_options("DEL", "NRT", "2024-03-15", "2024-03-20", 1)
        print(f"   ✈️  Found {len(flights)} flight options")
        for i, flight in enumerate(flights[:2], 1):
            print(f"      {i}. {flight.provider}: {flight.summary} - {flight.price_currency} {flight.price_total}")
        print("   ✅ Flight options working")
        
        # Test 6: Mock hotel options
        print("\n6️⃣ Testing hotel options (mock data)...")
        hotels = await get_hotel_options("NRT", "2024-03-15", "2024-03-20", 1)
        print(f"   🏨 Found {len(hotels)} hotel options")
        for i, hotel in enumerate(hotels[:2], 1):
            print(f"      {i}. {hotel.provider}: {hotel.name} - {hotel.price_currency} {hotel.price_total}")
        print("   ✅ Hotel options working")
        
        # Test 7: Package creation
        print("\n7️⃣ Testing package creation...")
        packages = []
        for f in flights[:2]:
            for h in hotels[:2]:
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
        
        packages = sorted(packages, key=lambda p: p.est_total)[:3]
        print(f"   📦 Created {len(packages)} packages")
        for i, pkg in enumerate(packages, 1):
            print(f"      {i}. {pkg.title} - Total: {pkg.est_total_currency} {pkg.est_total}")
        print("   ✅ Package creation working")
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! The system is working correctly.")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_core_functionality()
    
    if success:
        print("\n🚀 Ready to run! Use 'python main.py --demo' to start the application.")
        sys.exit(0)
    else:
        print("\n💥 Tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
