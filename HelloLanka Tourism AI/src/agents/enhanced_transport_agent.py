import json
import requests
from typing import List, Dict, Any
from contracts import TravelLeg
from settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE

class EnhancedTransportAgent:
    """
    Enhanced transport agent that uses LLM for intelligent travel recommendations.
    Provides multiple transport options with detailed explanations.
    """
    
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.base_url = GEMINI_BASE
    
    def get_transport_recommendations(self, from_city: str, to_city: str, 
                                    group_size: int, budget: str, 
                                    elderly_friendly: bool = False) -> List[TravelLeg]:
        """
        Get comprehensive transport recommendations using LLM.
        """
        try:
            if not self.api_key:
                return self._fallback_transport_options(from_city, to_city, group_size, budget)
            
            # Get LLM-powered transport recommendations
            recommendations = self._get_llm_transport_suggestions(
                from_city, to_city, group_size, budget, elderly_friendly
            )
            
            return recommendations
            
        except Exception as e:
            print(f"⚠️ LLM transport recommendation failed: {e}")
            return self._fallback_transport_options(from_city, to_city, group_size, budget)
    
    def _get_llm_transport_suggestions(self, from_city: str, to_city: str, 
                                     group_size: int, budget: str, 
                                     elderly_friendly: bool) -> List[TravelLeg]:
        """Get transport suggestions from LLM."""
        
        prompt = f"""
        You are a Sri Lankan transport expert. Recommend the best travel options for this journey:

        FROM: {from_city}
        TO: {to_city}
        GROUP SIZE: {group_size} people
        BUDGET: {budget}
        ELDERLY FRIENDLY: {'Yes - need comfortable, easy access' if elderly_friendly else 'No'}

        Consider these transport modes:
        1. Private Car/Taxi - Most flexible, comfortable
        2. Train - Scenic, affordable, cultural experience
        3. Bus - Budget-friendly, local experience
        4. Tuk-tuk - Short distances, local charm
        5. Walking - For nearby attractions

        For each recommended option, provide:
        - Mode of transport
        - Estimated distance and time
        - Cost per person or total
        - Why it's suitable for this traveler
        - Special considerations (elderly-friendly, scenic, etc.)

        Return ONLY a JSON array with this structure:
        [
            {{
                "mode": "car/train/bus/tuk/walk",
                "from": "{from_city}",
                "to": "{to_city}",
                "distance_km": 150,
                "duration_minutes": 180,
                "cost_per_person": 2000,
                "total_cost": 4000,
                "currency": "LKR",
                "reasoning": "Why this option is recommended",
                "elderly_friendly": true/false,
                "scenic_rating": 8,
                "comfort_level": "high/medium/low",
                "booking_info": "How to book or find this transport",
                "special_notes": "Any special considerations"
            }}
        ]

        Provide 3-4 different options with varying costs and experiences.
        """
        
        try:
            response = self._call_gemini(prompt)
            return self._parse_transport_response(response)
        except Exception as e:
            print(f"Error getting LLM transport suggestions: {e}")
            return self._fallback_transport_options(from_city, to_city, group_size, budget)
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API for transport recommendations."""
        url = self.base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a Sri Lankan transport expert specializing in personalized travel recommendations. Provide detailed, practical transport options with clear reasoning."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def _parse_transport_response(self, response: str) -> List[TravelLeg]:
        """Parse LLM response into TravelLeg objects."""
        try:
            # Extract JSON array from response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start == -1 or end <= start:
                return []
            
            json_str = response[start:end]
            data = json.loads(json_str)
            
            travel_legs = []
            for item in data:
                leg = TravelLeg(
                    mode=item.get("mode", "car"),
                    from_=item.get("from", ""),
                    to=item.get("to", ""),
                    eta_min=item.get("duration_minutes", 0),
                    km=item.get("distance_km", 0),
                    estimated_cost=item.get("total_cost", 0),
                    cost_currency=item.get("currency", "LKR"),
                    explanation=item.get("reasoning", "AI-recommended transport option")
                )
                
                # Add additional data
                leg_dict = leg.model_dump()
                leg_dict.update({
                    "scenic_rating": item.get("scenic_rating", 5),
                    "comfort_level": item.get("comfort_level", "medium"),
                    "elderly_friendly": item.get("elderly_friendly", False),
                    "booking_info": item.get("booking_info", ""),
                    "special_notes": item.get("special_notes", ""),
                    "cost_per_person": item.get("cost_per_person", 0)
                })
                
                travel_legs.append(TravelLeg(**leg_dict))
            
            return travel_legs
            
        except Exception as e:
            print(f"Error parsing transport response: {e}")
            return []
    
    def _fallback_transport_options(self, from_city: str, to_city: str, 
                                  group_size: int, budget: str) -> List[TravelLeg]:
        """Fallback transport options when LLM fails."""
        
        # Simple distance estimation
        distance = self._estimate_distance(from_city, to_city)
        duration = int(distance / 45 * 60)  # Assume 45 km/h average
        
        options = []
        
        # Private Car
        car_cost = int(distance * 15 * group_size)
        options.append(TravelLeg(
            mode="car",
            from_=from_city,
            to=to_city,
            eta_min=duration,
            km=distance,
            estimated_cost=car_cost,
            cost_currency="LKR",
            explanation=f"Private car from {from_city} to {to_city} - most flexible option",
            scenic_rating=7,
            comfort_level="high",
            elderly_friendly=True,
            booking_info="Book through hotel or local taxi service"
        ))
        
        # Train (if distance > 50km)
        if distance > 50:
            train_cost = int(distance * 2 * group_size)
            options.append(TravelLeg(
                mode="train",
                from_=from_city,
                to=to_city,
                eta_min=duration + 30,  # Trains are slower
                km=distance,
                estimated_cost=train_cost,
                cost_currency="LKR",
                explanation=f"Scenic train journey from {from_city} to {to_city} - cultural experience",
                scenic_rating=9,
                comfort_level="medium",
                elderly_friendly=True,
                booking_info="Book at railway station or online"
            ))
        
        # Bus
        bus_cost = int(distance * 1.5 * group_size)
        options.append(TravelLeg(
            mode="bus",
            from_=from_city,
            to=to_city,
            eta_min=duration + 15,
            km=distance,
            estimated_cost=bus_cost,
            cost_currency="LKR",
            explanation=f"Local bus from {from_city} to {to_city} - budget-friendly option",
            scenic_rating=6,
            comfort_level="low",
            elderly_friendly=False,
            booking_info="Buy tickets at bus station"
        ))
        
        return options
    
    def _estimate_distance(self, from_city: str, to_city: str) -> int:
        """Estimate distance between cities."""
        # Simple distance mapping for major Sri Lankan cities
        distances = {
            ("colombo", "kandy"): 120,
            ("colombo", "galle"): 120,
            ("colombo", "jaffna"): 400,
            ("colombo", "anuradhapura"): 200,
            ("kandy", "galle"): 150,
            ("kandy", "jaffna"): 350,
            ("galle", "jaffna"): 450,
        }
        
        key = (from_city.lower(), to_city.lower())
        reverse_key = (to_city.lower(), from_city.lower())
        
        return distances.get(key, distances.get(reverse_key, 100))  # Default 100km
    
    def optimize_itinerary_transport(self, itinerary_data: Dict[str, Any], 
                                   group_size: int, budget_currency: str) -> Dict[str, Any]:
        """
        Optimize transportation for an entire itinerary.
        """
        print(f"🚗 Optimizing transport for {group_size} people with {budget_currency} budget")
        
        enhanced_daily_plan = []
        
        for day_data in itinerary_data.get("daily_plan", []):
            enhanced_day = day_data.copy()
            enhanced_travel_legs = []
            
            # Get transport recommendations for each travel leg
            for leg_data in day_data.get("travel_legs", []):
                from_place = leg_data.get("from", leg_data.get("from_", ""))
                to_place = leg_data.get("to", "")
                
                if from_place and to_place:
                    # Get multiple transport options
                    recommendations = self.get_transport_recommendations(
                        from_place, to_place, group_size, budget_currency
                    )
                    enhanced_travel_legs.extend(recommendations)
                else:
                    enhanced_travel_legs.append(leg_data)
            
            enhanced_day["travel_legs"] = enhanced_travel_legs
            enhanced_daily_plan.append(enhanced_day)
        
        # Update itinerary with enhanced transport
        enhanced_itinerary = itinerary_data.copy()
        enhanced_itinerary["daily_plan"] = enhanced_daily_plan
        
        return enhanced_itinerary
