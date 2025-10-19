import json
import requests
from typing import List, Dict, Any, Optional
from settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE

class AccommodationAgent:
    """
    Agent responsible for finding and recommending accommodations based on user preferences.
    Uses LLM to suggest hotels with pricing and detailed information.
    """
    
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.base_url = GEMINI_BASE
    
    def find_accommodations(self, location: str, budget_per_day: float, 
                          currency: str, accommodation_types: List[str], 
                          group_size: int, elderly_friendly: bool = False,
                          special_requirements: str = "") -> List[Dict[str, Any]]:
        """
        Find accommodations using LLM with real pricing and details.
        
        Args:
            location: City or area name
            budget_per_day: Daily budget in the specified currency
            currency: Currency code (USD, LKR, etc.)
            accommodation_types: List of preferred types (hotel, resort, etc.)
            group_size: Number of people
            elderly_friendly: Whether accommodations should be elderly-friendly
            special_requirements: Any special requirements
            
        Returns:
            List of accommodation recommendations with pricing
        """
        try:
            if not self.api_key:
                return self._fallback_accommodations(location, budget_per_day, currency, accommodation_types)
            
            # Convert budget to LKR for consistent pricing
            budget_lkr = self._convert_to_lkr(budget_per_day, currency)
            
            prompt = self._build_accommodation_prompt(
                location, budget_lkr, accommodation_types, group_size, 
                elderly_friendly, special_requirements
            )
            
            response = self._call_gemini(prompt)
            accommodations = self._parse_accommodation_response(response)
            
            # Add pricing details and convert back to requested currency
            for acc in accommodations:
                acc['price_per_night'] = self._convert_from_lkr(acc.get('price_lkr', 0), currency)
                acc['currency'] = currency
                acc['total_cost'] = acc['price_per_night'] * group_size
            
            return accommodations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            print(f"Error finding accommodations: {e}")
            return self._fallback_accommodations(location, budget_per_day, currency, accommodation_types)
    
    def _build_accommodation_prompt(self, location: str, budget_lkr: float, 
                                  accommodation_types: List[str], group_size: int,
                                  elderly_friendly: bool, special_requirements: str) -> str:
        """Build a detailed prompt for accommodation recommendations."""
        
        elderly_notes = ""
        if elderly_friendly:
            elderly_notes = "IMPORTANT: Prioritize accommodations that are elderly-friendly with features like: elevators, ground floor rooms, wheelchair accessibility, easy access to facilities, and comfortable amenities."
        
        special_notes = ""
        if special_requirements:
            special_notes = f"Special requirements: {special_requirements}"
        
        prompt = f"""
        Find 5 specific accommodation recommendations in {location}, Sri Lanka with the following criteria:
        
        Budget: {budget_lkr} LKR per night for {group_size} people
        Preferred types: {', '.join(accommodation_types)}
        {elderly_notes}
        {special_notes}
        
        For each accommodation, provide:
        1. Name (specific hotel/resort name)
        2. Type (hotel/resort/villa/guesthouse)
        3. Location (specific area within {location})
        4. Price in LKR per night
        5. Rating (1-5 stars)
        6. Key features (amenities, services)
        7. Why it's suitable for this traveler
        8. Contact information (phone/website if available)
        
        Return ONLY a JSON array with this exact structure:
        [
            {{
                "name": "Hotel Name",
                "type": "hotel",
                "location": "Specific Area",
                "price_lkr": 15000,
                "rating": 4.5,
                "features": ["Free WiFi", "Pool", "Restaurant"],
                "description": "Why this is suitable",
                "contact": {{
                    "phone": "+94 XX XXX XXXX",
                    "website": "www.hotel.com"
                }}
            }}
        ]
        
        Focus on real, well-known accommodations in {location}. Ensure prices are realistic for Sri Lankan market.
        """
        
        return prompt
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API for accommodation recommendations."""
        url = self.base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a Sri Lankan travel expert specializing in accommodation recommendations. Provide accurate, detailed information about hotels and resorts."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def _parse_accommodation_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the LLM response into accommodation data."""
        try:
            # Extract JSON array from response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start == -1 or end <= start:
                return []
            
            json_str = response[start:end]
            accommodations = json.loads(json_str)
            
            if isinstance(accommodations, list):
                return accommodations
            else:
                return []
                
        except Exception as e:
            print(f"Error parsing accommodation response: {e}")
            return []
    
    def _convert_to_lkr(self, amount: float, currency: str) -> float:
        """Convert amount to LKR for consistent pricing."""
        # Simple conversion rates (in production, use real-time rates)
        rates = {
            "USD": 300,
            "EUR": 320,
            "GBP": 380,
            "LKR": 1,
            "INR": 3.6
        }
        return amount * rates.get(currency.upper(), 300)  # Default to USD rate
    
    def _convert_from_lkr(self, amount_lkr: float, currency: str) -> float:
        """Convert LKR amount to requested currency."""
        rates = {
            "USD": 300,
            "EUR": 320,
            "GBP": 380,
            "LKR": 1,
            "INR": 3.6
        }
        return amount_lkr / rates.get(currency.upper(), 300)
    
    def _fallback_accommodations(self, location: str, budget_per_day: float, 
                               currency: str, accommodation_types: List[str]) -> List[Dict[str, Any]]:
        """Fallback accommodations when LLM is not available."""
        
        # Convert budget to LKR for fallback
        budget_lkr = self._convert_to_lkr(budget_per_day, currency)
        
        # Base accommodations by location
        base_accommodations = {
            "colombo": [
                {
                    "name": "Cinnamon Grand Colombo",
                    "type": "hotel",
                    "location": "Colombo 3",
                    "price_lkr": 25000,
                    "rating": 4.5,
                    "features": ["5-star luxury", "Multiple restaurants", "Spa", "Pool"],
                    "description": "Luxury hotel in the heart of Colombo with excellent facilities",
                    "contact": {"phone": "+94 11 2XXX XXXX", "website": "www.cinnamonhotels.com"}
                },
                {
                    "name": "Galle Face Hotel",
                    "type": "hotel",
                    "location": "Colombo 3",
                    "price_lkr": 20000,
                    "rating": 4.3,
                    "features": ["Historic hotel", "Ocean view", "Heritage charm", "Restaurant"],
                    "description": "Historic colonial hotel with ocean views and heritage charm",
                    "contact": {"phone": "+94 11 2XXX XXXX", "website": "www.gallefacehotel.com"}
                }
            ],
            "kandy": [
                {
                    "name": "Earl's Regency Hotel",
                    "type": "hotel",
                    "location": "Kandy",
                    "price_lkr": 18000,
                    "rating": 4.4,
                    "features": ["Mountain views", "Pool", "Restaurant", "Spa"],
                    "description": "Comfortable hotel with beautiful mountain views",
                    "contact": {"phone": "+94 81 2XXX XXXX", "website": "www.earlsregency.com"}
                }
            ],
            "galle": [
                {
                    "name": "Galle Fort Hotel",
                    "type": "hotel",
                    "location": "Galle Fort",
                    "price_lkr": 22000,
                    "rating": 4.6,
                    "features": ["Historic fort location", "Boutique hotel", "Restaurant", "Garden"],
                    "description": "Boutique hotel within the historic Galle Fort",
                    "contact": {"phone": "+94 91 2XXX XXXX", "website": "www.galleforthotel.com"}
                }
            ]
        }
        
        # Get accommodations for the location or default
        location_key = location.lower().replace(" ", "_")
        accommodations = base_accommodations.get(location_key, base_accommodations["colombo"])
        
        # Filter by budget and add pricing
        filtered_accommodations = []
        for acc in accommodations:
            if acc["price_lkr"] <= budget_lkr * 1.2:  # Allow 20% over budget
                acc["price_per_night"] = self._convert_from_lkr(acc["price_lkr"], currency)
                acc["currency"] = currency
                filtered_accommodations.append(acc)
        
        return filtered_accommodations[:3]  # Return top 3 fallback options
