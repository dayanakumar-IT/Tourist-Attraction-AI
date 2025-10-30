import math, datetime as dt, random
from typing import List, Dict, Tuple, Any
from contracts import TripNormalized, Itinerary, DayPlan, Activity, TravelLeg, BudgetSummary
from tools.sri_lanka_coordinates import get_coordinates, calculate_distance, get_travel_time
from tools.sri_lanka_places import get_real_sri_lanka_places
from tools.unsplash_images import get_sri_lanka_place_image

class FallbackPlannerAgent:
    """
    Fallback planner agent that works without LLM API.
    Uses predefined Sri Lankan places and intelligent routing.
    """
    
    def __init__(self):
        self.sri_lanka_places = {
            "colombo": [
                {"name": "Gangaramaya Temple", "type": "cultural", "reason": "Important Buddhist temple in Colombo", "elderly_friendly": True},
                {"name": "Independence Memorial Hall", "type": "cultural", "reason": "Historic monument with beautiful architecture", "elderly_friendly": True},
                {"name": "Colombo National Museum", "type": "cultural", "reason": "Rich collection of Sri Lankan artifacts", "elderly_friendly": True},
                {"name": "Galle Face Green", "type": "nature", "reason": "Beautiful oceanfront park perfect for evening walks", "elderly_friendly": True},
                {"name": "Pettah Market", "type": "food", "reason": "Vibrant local market with authentic Sri Lankan food", "elderly_friendly": False}
            ],
            "kandy": [
                {"name": "Temple of the Sacred Tooth Relic", "type": "cultural", "reason": "Most sacred Buddhist temple in Sri Lanka", "elderly_friendly": True},
                {"name": "Kandy Lake", "type": "nature", "reason": "Peaceful lake perfect for leisurely walks", "elderly_friendly": True},
                {"name": "Royal Botanical Gardens", "type": "nature", "reason": "Beautiful gardens with easy walking paths", "elderly_friendly": True},
                {"name": "Kandy Cultural Show", "type": "cultural", "reason": "Traditional Sri Lankan dance and music performance", "elderly_friendly": True},
                {"name": "Udawattakele Forest Reserve", "type": "nature", "reason": "Nature reserve with hiking trails", "elderly_friendly": False}
            ],
            "galle": [
                {"name": "Galle Fort", "type": "cultural", "reason": "UNESCO World Heritage site with colonial architecture", "elderly_friendly": True},
                {"name": "Galle Lighthouse", "type": "cultural", "reason": "Historic lighthouse with ocean views", "elderly_friendly": True},
                {"name": "Dutch Reformed Church", "type": "cultural", "reason": "Beautiful colonial church with rich history", "elderly_friendly": True},
                {"name": "Galle Fort Ramparts", "type": "cultural", "reason": "Historic fortifications with scenic views", "elderly_friendly": True},
                {"name": "Galle Fort Shopping", "type": "food", "reason": "Local shops and cafes in historic setting", "elderly_friendly": True}
            ],
            "jaffna": [
                {"name": "Jaffna Fort", "type": "cultural", "reason": "Historic Dutch fort with easy access", "elderly_friendly": True},
                {"name": "Nallur Kandaswamy Temple", "type": "cultural", "reason": "Beautiful Hindu temple with cultural significance", "elderly_friendly": True},
                {"name": "Jaffna Public Library", "type": "cultural", "reason": "Symbol of Tamil culture and history", "elderly_friendly": True},
                {"name": "Jaffna Market", "type": "food", "reason": "Local market with Tamil cuisine and crafts", "elderly_friendly": False},
                {"name": "Point Pedro Lighthouse", "type": "cultural", "reason": "Northernmost point of Sri Lanka", "elderly_friendly": True}
            ],
            "anuradhapura": [
                {"name": "Ruwanwelisaya", "type": "cultural", "reason": "Ancient Buddhist stupa and pilgrimage site", "elderly_friendly": True},
                {"name": "Jetavanaramaya", "type": "cultural", "reason": "Historic Buddhist monastery ruins", "elderly_friendly": True},
                {"name": "Sri Maha Bodhi", "type": "cultural", "reason": "Sacred Bodhi tree, oldest documented tree in the world", "elderly_friendly": True},
                {"name": "Abhayagiri Monastery", "type": "cultural", "reason": "Ancient monastery with archaeological significance", "elderly_friendly": True},
                {"name": "Anuradhapura Museum", "type": "cultural", "reason": "Museum showcasing ancient artifacts", "elderly_friendly": True}
            ]
        }
    
    def plan(self, req: TripNormalized) -> List[Itinerary]:
        """Create itineraries using fallback data."""
        print(f"Using fallback planner for: {req.start_location} -> {req.destinations}")
        
        # Plan route through destinations
        route_plan = self._plan_multi_destination_route(req)
        
        # Create different itinerary variants
        variants = [
            ("Cultural Explorer", "Focus on cultural and historical sites"),
            ("Nature Lover", "Emphasize natural attractions and outdoor experiences"),
            ("Balanced Adventure", "Mix of culture, nature, and unique experiences")
        ]
        
        itineraries = []
        
        for variant_name, variant_description in variants:
            daily_plans = []
            dates = self._get_dates(req.start_date, req.trip_days)
            
            for i, date in enumerate(dates):
                # Determine which destination to visit on this day
                if i < len(route_plan):
                    base_city = route_plan[i]["city"]
                else:
                    base_city = route_plan[-1]["city"] if route_plan else req.start_location
                
                # Get places for this city
                places = self._get_places_for_city(base_city, req.themes, req.party.elderly)
                
                # Create activities from places
                activities = self._create_activities_from_places(places, req.party.elderly, base_city)
                
                # Add travel legs with real travel times
                travel_legs = []
                if i == 0 and base_city != req.start_location:
                    travel_legs = self._create_travel_leg_with_time(req.start_location, base_city)
                elif i > 0 and base_city != route_plan[i-1]["city"]:
                    travel_legs = self._create_travel_leg_with_time(route_plan[i-1]["city"], base_city)
                
                daily_plan = DayPlan(
                    date=date,
                    base_city=base_city,
                    activities=activities,
                    travel_legs=travel_legs,
                    notes=[f"Fallback Planning: {variant_description}"]
                )
                
                daily_plans.append(daily_plan)
            
            # Create itinerary
            destination_names = [stop["city"] for stop in route_plan]
            itinerary = Itinerary(
                title=f"{variant_name} – {' → '.join(destination_names)}",
                theme_mix=req.themes,
                town_order=destination_names,
                daily_plan=daily_plans,
                budget_summary=BudgetSummary(currency=req.budget.currency, breakdown={})
            )
            
            itineraries.append(itinerary)
        
        return itineraries[:3]
    
    def _plan_multi_destination_route(self, req: TripNormalized) -> List[Dict[str, Any]]:
        """Plan optimal route through multiple destinations."""
        if not req.destinations:
            return [{"city": req.start_location, "day": 1}]
        
        route = []
        current = req.start_location
        remaining = req.destinations.copy()
        
        # Greedy algorithm to find shortest route
        for day in range(min(req.trip_days, len(req.destinations) + 1)):
            if day == 0 and req.destinations:
                # First day: go to nearest destination
                nearest = min(remaining, key=lambda x: calculate_distance(current, x))
                route.append({"city": nearest, "day": day + 1})
                remaining.remove(nearest)
                current = nearest
            elif remaining:
                # Subsequent days: go to next nearest destination
                nearest = min(remaining, key=lambda x: calculate_distance(current, x))
                route.append({"city": nearest, "day": day + 1})
                remaining.remove(nearest)
                current = nearest
            else:
                # Stay in last destination
                route.append({"city": current, "day": day + 1})
        
        return route
    
    def _get_places_for_city(self, city: str, themes: List[str], elderly_friendly: bool) -> List[Dict[str, Any]]:
        """Get places for a specific city based on themes."""
        city_lower = city.lower()
        places = self.sri_lanka_places.get(city_lower, [])
        
        # Filter by themes
        if themes:
            filtered_places = []
            for place in places:
                if any(theme.lower() in place["type"].lower() for theme in themes):
                    filtered_places.append(place)
            places = filtered_places if filtered_places else places
        
        # Filter for elderly-friendly if needed
        if elderly_friendly:
            places = [p for p in places if p.get("elderly_friendly", False)]
        
        return places[:3]  # Return top 3 places
    
    def _create_activities_from_places(self, places: List[Dict[str, Any]], elderly_friendly: bool, base_city: str) -> List[Activity]:
        """Create Activity objects from places."""
        activities = []
        
        for i, place in enumerate(places):
            # Determine start time based on elderly needs
            if elderly_friendly:
                start_times = ["09:00", "11:30", "14:00"]
            else:
                start_times = ["08:30", "11:00", "14:00"]
            
            start_time = start_times[min(i, len(start_times) - 1)]
            
            # Get real coordinates for the place
            lat, lon = get_coordinates(place["name"])
            
            activity = Activity(
                name=place["name"],
                kind=place["type"],
                start=start_time,
                duration_min=120,  # 2 hours default
                poi_id=None,
                lat=lat,
                lon=lon
            )
            
            # Add explainable AI data
            activity_dict = activity.model_dump()
            activity_dict.update({
                "ai_reasoning": place.get("reason", "Fallback-selected based on your interests"),
                "elderly_friendly": place.get("elderly_friendly", False),
                "estimated_duration": "2-3 hours",
                "best_time": "morning",
                "cost_range": "LKR 200-500",
                "explanation": f"Selected because: {place.get('reason', 'Matches your interests')}",
                "difficulty_level": "Easy" if place.get("elderly_friendly", False) else "Moderate"
            })
            
            # Add image data
            try:
                image_data = get_sri_lanka_place_image(place["name"])
                if image_data:
                    activity_dict.update({
                        "image_url": image_data["url"],
                        "image_alt": image_data["alt"],
                        "photographer": image_data["photographer"],
                        "photographer_url": image_data["photographer_url"]
                    })
                    print(f"Added image for {place['name']}: {image_data['url']}")
                else:
                    print(f"No image found for {place['name']}")
            except Exception as e:
                print(f"Error fetching image for {place['name']}: {e}")
            
            activities.append(Activity(**activity_dict))
        
        return activities
    
    def _create_travel_leg_with_time(self, from_city: str, to_city: str) -> List[TravelLeg]:
        """Create travel leg with real travel time calculation."""
        distance = calculate_distance(from_city, to_city)
        
        # Get travel time for different modes
        car_time = get_travel_time(from_city, to_city, "car")
        train_time = get_travel_time(from_city, to_city, "train")
        bus_time = get_travel_time(from_city, to_city, "bus")
        
        # Create multiple transport options
        legs = []
        
        # Car option
        legs.append(TravelLeg(
            mode="car",
            from_=from_city,
            to=to_city,
            eta_min=car_time,
            km=round(distance, 1),
            estimated_cost=int(distance * 15),  # LKR per km
            cost_currency="LKR",
            explanation=f"Direct drive from {from_city} to {to_city} - most flexible option",
            scenic_rating=7,
            comfort_level="high",
            elderly_friendly=True
        ))
        
        # Train option (if distance > 50km)
        if distance > 50:
            legs.append(TravelLeg(
                mode="train",
                from_=from_city,
                to=to_city,
                eta_min=train_time,
                km=round(distance, 1),
                estimated_cost=int(distance * 2),
                cost_currency="LKR",
                explanation=f"Scenic train journey from {from_city} to {to_city} - cultural experience",
                scenic_rating=9,
                comfort_level="medium",
                elderly_friendly=True
            ))
        
        # Bus option
        legs.append(TravelLeg(
            mode="bus",
            from_=from_city,
            to=to_city,
            eta_min=bus_time,
            km=round(distance, 1),
            estimated_cost=int(distance * 1.5),
            cost_currency="LKR",
            explanation=f"Local bus from {from_city} to {to_city} - budget-friendly option",
            scenic_rating=6,
            comfort_level="low",
            elderly_friendly=False
        ))
        
        return legs
    
    def _get_dates(self, start_date, n: int) -> List[str]:
        """Get list of dates for the trip."""
        if isinstance(start_date, dt.date):
            d0 = start_date
        else:
            d0 = dt.date.fromisoformat(str(start_date))
        return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(n)]
