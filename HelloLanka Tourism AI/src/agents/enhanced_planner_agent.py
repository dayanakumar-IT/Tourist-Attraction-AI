import math, datetime as dt, random
from typing import List, Dict, Tuple, Any
from contracts import TripNormalized, Itinerary, DayPlan, Activity, TravelLeg, BudgetSummary
from tools.geocode import geocode_nominatim
from tools.pois import (
    search_radius,
    search_radius_general_filtered,
    search_radius_name_filtered_multi,
)
from tools.unsplash_images import get_sri_lanka_place_image
from tools.sri_lanka_places import get_real_sri_lanka_places
from settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE
import json
import requests

class EnhancedPlannerAgent:
    """
    Enhanced planner agent that uses LLM for intelligent place selection and reasoning.
    Provides explainable AI for all decisions.
    """
    
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.base_url = GEMINI_BASE
    
    def plan(self, req: TripNormalized) -> List[Itinerary]:
        """
        Enhanced planning with LLM-powered place selection and reasoning.
        """
        print(f"🧠 Enhanced planning for {req.start_location} → {req.destinations}")
        
        # Get intelligent place suggestions using LLM
        place_suggestions = self._get_llm_place_suggestions(req)
        print(f"🎯 LLM suggested places: {place_suggestions}")
        
        # Create itineraries with explainable AI
        itineraries = self._create_explainable_itineraries(req, place_suggestions)
        
        return itineraries[:3]  # Return top 3 variants
    
    def _get_llm_place_suggestions(self, req: TripNormalized) -> Dict[str, List[Dict[str, Any]]]:
        """
        Use LLM to intelligently suggest places based on interests and destinations.
        """
        try:
            if not self.api_key:
                return self._fallback_place_suggestions(req)
            
            # Build comprehensive prompt for LLM
            prompt = self._build_place_suggestion_prompt(req)
            
            # Call LLM
            response = self._call_gemini(prompt)
            suggestions = self._parse_llm_response(response)
            
            return suggestions
            
        except Exception as e:
            print(f"⚠️ LLM place suggestion failed: {e}")
            return self._fallback_place_suggestions(req)
    
    def _build_place_suggestion_prompt(self, req: TripNormalized) -> str:
        """Build a comprehensive prompt for LLM place suggestions."""
        
        destinations_text = ", ".join(req.destinations) if req.destinations else "No specific destinations (interest-based planning)"
        elderly_notes = "IMPORTANT: This traveler is elderly and needs easy access, comfortable seating, and gentle terrain." if req.party.elderly else ""
        group_notes = f"Traveling as {req.party.type} group of {req.party.count} people."
        
        prompt = f"""
        You are a Sri Lankan travel expert. Suggest specific places for a {req.trip_days}-day trip based on these details:

        START LOCATION: {req.start_location}
        DESTINATIONS: {destinations_text}
        INTERESTS/THEMES: {', '.join(req.themes)}
        GROUP: {group_notes}
        {elderly_notes}
        BUDGET: {req.budget.currency} {req.budget.amount} total
        SPECIAL REQUIREMENTS: {req.party.notes}

        For each day, suggest 2-3 specific places that:
        1. Match the traveler's interests
        2. Are appropriate for the destination (if specified)
        3. Consider elderly needs (if applicable)
        4. Are realistic for the budget and group size
        5. Include a mix of cultural, natural, and unique experiences

        Return ONLY a JSON object with this exact structure:
        {{
            "reasoning": "Brief explanation of why these places were selected",
            "daily_suggestions": {{
                "day_1": {{
                    "base_city": "City Name",
                    "places": [
                        {{
                            "name": "Specific Place Name",
                            "type": "cultural/natural/adventure/food/etc",
                            "reason": "Why this place is perfect for this traveler",
                            "elderly_friendly": true/false,
                            "estimated_duration": "2-3 hours",
                            "best_time": "morning/afternoon/evening",
                            "cost_range": "Free - LKR 500"
                        }}
                    ]
                }},
                "day_2": {{
                    "base_city": "City Name",
                    "places": [...]
                }}
            }}
        }}

        Focus on REAL, SPECIFIC places in Sri Lanka. Be creative but realistic.
        """
        
        return prompt
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API for place suggestions."""
        url = self.base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a Sri Lankan travel expert specializing in personalized itinerary planning. Provide specific, realistic place recommendations with clear reasoning."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def _parse_llm_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse LLM response into structured place suggestions."""
        try:
            # Extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start == -1 or end <= start:
                return {}
            
            json_str = response[start:end]
            data = json.loads(json_str)
            
            return data.get("daily_suggestions", {})
            
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return {}
    
    def _fallback_place_suggestions(self, req: TripNormalized) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback place suggestions when LLM fails."""
        suggestions = {}
        
        # Use destinations or start location
        cities = req.destinations if req.destinations else [req.start_location]
        
        for i, city in enumerate(cities):
            day_key = f"day_{i+1}"
            suggestions[day_key] = {
                "base_city": city,
                "places": self._get_fallback_places_for_city(city, req.themes, req.party.elderly)
            }
        
        return suggestions
    
    def _get_fallback_places_for_city(self, city: str, themes: List[str], elderly_friendly: bool) -> List[Dict[str, Any]]:
        """Get fallback places for a specific city."""
        city_lower = city.lower()
        
        # City-specific place mappings
        city_places = {
            "jaffna": [
                {"name": "Jaffna Fort", "type": "cultural", "reason": "Historic Dutch fort with easy access", "elderly_friendly": True},
                {"name": "Nallur Kandaswamy Temple", "type": "cultural", "reason": "Beautiful Hindu temple with cultural significance", "elderly_friendly": True},
                {"name": "Jaffna Public Library", "type": "cultural", "reason": "Symbol of Tamil culture and history", "elderly_friendly": True}
            ],
            "colombo": [
                {"name": "Gangaramaya Temple", "type": "cultural", "reason": "Important Buddhist temple in the heart of Colombo", "elderly_friendly": True},
                {"name": "Independence Memorial Hall", "type": "cultural", "reason": "Historic monument with beautiful architecture", "elderly_friendly": True},
                {"name": "Colombo National Museum", "type": "cultural", "reason": "Rich collection of Sri Lankan artifacts", "elderly_friendly": True}
            ],
            "kandy": [
                {"name": "Temple of the Sacred Tooth Relic", "type": "cultural", "reason": "Most sacred Buddhist temple in Sri Lanka", "elderly_friendly": True},
                {"name": "Kandy Lake", "type": "nature", "reason": "Peaceful lake perfect for leisurely walks", "elderly_friendly": True},
                {"name": "Royal Botanical Gardens", "type": "nature", "reason": "Beautiful gardens with easy walking paths", "elderly_friendly": True}
            ],
            "galle": [
                {"name": "Galle Fort", "type": "cultural", "reason": "UNESCO World Heritage site with colonial architecture", "elderly_friendly": True},
                {"name": "Galle Lighthouse", "type": "cultural", "reason": "Historic lighthouse with ocean views", "elderly_friendly": True},
                {"name": "Dutch Reformed Church", "type": "cultural", "reason": "Beautiful colonial church with rich history", "elderly_friendly": True}
            ]
        }
        
        places = city_places.get(city_lower, [
            {"name": f"{city} Cultural Center", "type": "cultural", "reason": "Local cultural attraction", "elderly_friendly": True},
            {"name": f"{city} Market", "type": "food", "reason": "Experience local culture and cuisine", "elderly_friendly": True}
        ])
        
        # Filter for elderly-friendly if needed
        if elderly_friendly:
            places = [p for p in places if p.get("elderly_friendly", False)]
        
        return places[:3]  # Return top 3 places
    
    def _create_explainable_itineraries(self, req: TripNormalized, place_suggestions: Dict[str, List[Dict[str, Any]]]) -> List[Itinerary]:
        """Create itineraries with explainable AI reasoning."""
        itineraries = []
        
        # Create different itinerary variants
        variants = [
            ("Cultural Explorer", "Focus on cultural and historical sites"),
            ("Nature Lover", "Emphasize natural attractions and outdoor experiences"),
            ("Balanced Adventure", "Mix of culture, nature, and unique experiences")
        ]
        
        for variant_name, variant_description in variants:
            daily_plans = []
            dates = self._get_dates(req.start_date, req.trip_days)
            
            for i, date in enumerate(dates):
                day_key = f"day_{i+1}"
                day_suggestions = place_suggestions.get(day_key, {})
                
                base_city = day_suggestions.get("base_city", req.start_location)
                places = day_suggestions.get("places", [])
                
                # Create activities from LLM suggestions
                activities = self._create_activities_from_suggestions(places, req.party.elderly)
                
                # Add travel legs if needed
                travel_legs = []
                if i == 0 and base_city != req.start_location:
                    travel_legs = self._create_travel_leg(req.start_location, base_city)
                
                daily_plan = DayPlan(
                    date=date,
                    base_city=base_city,
                    activities=activities,
                    travel_legs=travel_legs,
                    notes=[f"AI Reasoning: {variant_description}"]
                )
                
                daily_plans.append(daily_plan)
            
            # Create itinerary
            itinerary = Itinerary(
                title=f"{variant_name} – {req.destinations[0] if req.destinations else req.start_location} & Beyond",
                theme_mix=req.themes,
                town_order=req.destinations,
                daily_plan=daily_plans,
                budget_summary=BudgetSummary(currency=req.budget.currency, breakdown={})
            )
            
            itineraries.append(itinerary)
        
        return itineraries
    
    def _create_activities_from_suggestions(self, places: List[Dict[str, Any]], elderly_friendly: bool) -> List[Activity]:
        """Create Activity objects from LLM place suggestions."""
        activities = []
        
        for i, place in enumerate(places):
            # Determine start time based on elderly needs
            if elderly_friendly:
                start_times = ["09:00", "11:30", "14:00"]
            else:
                start_times = ["08:30", "11:00", "14:00"]
            
            start_time = start_times[min(i, len(start_times) - 1)]
            
            activity = Activity(
                name=place["name"],
                kind=place["type"],
                start=start_time,
                duration_min=120,  # 2 hours default
                poi_id=None,
                lat=None,
                lon=None
            )
            
            # Add explainable AI data
            activity_dict = activity.model_dump()
            activity_dict.update({
                "ai_reasoning": place.get("reason", "AI-selected based on your interests"),
                "elderly_friendly": place.get("elderly_friendly", False),
                "estimated_duration": place.get("estimated_duration", "2-3 hours"),
                "best_time": place.get("best_time", "morning"),
                "cost_range": place.get("cost_range", "LKR 200-500"),
                "explanation": f"Selected because: {place.get('reason', 'Matches your interests')}",
                "difficulty_level": "Easy" if place.get("elderly_friendly", False) else "Moderate"
            })
            
            # Add image
            try:
                image_data = get_sri_lanka_place_image(place["name"])
                if image_data:
                    activity_dict.update({
                        "image_url": image_data["url"],
                        "image_alt": image_data["alt"],
                        "photographer": image_data["photographer"],
                        "photographer_url": image_data["photographer_url"]
                    })
            except:
                pass
            
            activities.append(Activity(**activity_dict))
        
        return activities
    
    def _create_travel_leg(self, from_city: str, to_city: str) -> List[TravelLeg]:
        """Create travel leg between cities."""
        # Simple distance estimation
        distance = random.randint(50, 200)  # km
        duration = int(distance / 45 * 60)  # minutes
        
        return [TravelLeg(
            mode="car",
            from_=from_city,
            to=to_city,
            eta_min=duration,
            km=distance,
            estimated_cost=int(distance * 15),  # LKR per km
            cost_currency="LKR",
            explanation=f"Recommended route from {from_city} to {to_city} with scenic views"
        )]
    
    def _get_dates(self, start_date, n: int) -> List[str]:
        """Get list of dates for the trip."""
        if isinstance(start_date, dt.date):
            d0 = start_date
        else:
            d0 = dt.date.fromisoformat(str(start_date))
        return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(n)]
