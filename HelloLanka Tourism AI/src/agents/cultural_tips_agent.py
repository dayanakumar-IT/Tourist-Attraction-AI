"""
Cultural Tips Agent - Provides cultural advice, dress codes, and safety tips
for Sri Lankan tourism destinations.
"""

from typing import Dict, List, Any, Optional
from contracts import Activity, DayPlan
import random

class CulturalTipsAgent:
    def __init__(self):
        self.cultural_tips = {
            "temple": {
                "dress_code": "Cover shoulders and knees. Remove shoes and hats. No shorts or sleeveless tops.",
                "behavior": "Speak quietly, no photography of worshippers, remove shoes before entering.",
                "timing": "Best visited early morning (6-8 AM) or evening (6-8 PM) for peaceful experience.",
                "safety": "Keep valuables secure, be respectful of local customs."
            },
            "fort": {
                "dress_code": "Comfortable walking shoes, light clothing, hat for sun protection.",
                "behavior": "Follow designated paths, no climbing on walls or structures.",
                "timing": "Early morning or late afternoon to avoid heat, sunset views are spectacular.",
                "safety": "Stay on marked paths, be cautious on uneven surfaces."
            },
            "beach": {
                "dress_code": "Swimwear acceptable, cover up when leaving beach area.",
                "behavior": "Respect local beach etiquette, clean up after yourself.",
                "timing": "Best 6-10 AM and 4-7 PM, avoid midday sun.",
                "safety": "Swim only in designated areas, beware of strong currents, protect from sun."
            },
            "market": {
                "dress_code": "Comfortable clothes, closed shoes, avoid expensive jewelry.",
                "behavior": "Bargain politely, ask permission before taking photos of vendors.",
                "timing": "Early morning (6-9 AM) for fresh produce, evening for street food.",
                "safety": "Keep bags close, beware of pickpockets, don't flash money."
            },
            "national_park": {
                "dress_code": "Neutral colors (brown, green, beige), comfortable walking shoes.",
                "behavior": "Stay quiet, follow guide instructions, no feeding animals.",
                "timing": "Early morning (6-8 AM) or late afternoon (4-6 PM) for best wildlife viewing.",
                "safety": "Stay in vehicle during safari, keep distance from wild animals."
            }
        }
        
        self.safety_tips = {
            "crowded_areas": [
                "Keep your belongings secure and close to your body",
                "Be aware of your surroundings and avoid isolated areas",
                "Don't carry large amounts of cash or expensive jewelry",
                "Use hotel safes for valuables and important documents"
            ],
            "transportation": [
                "Use registered taxi services or ride-sharing apps",
                "Agree on fare before starting the journey",
                "Keep emergency contact numbers handy",
                "Avoid traveling alone at night in unfamiliar areas"
            ],
            "food_safety": [
                "Drink bottled water and avoid ice in drinks",
                "Eat at busy restaurants with good hygiene practices",
                "Wash hands before eating and carry hand sanitizer",
                "Try local food gradually to avoid stomach issues"
            ]
        }

    def get_cultural_tips(self, activity_name: str, location: str, activity_type: str = None) -> Dict[str, Any]:
        """Get cultural tips based on activity type and location."""
        activity_lower = activity_name.lower()
        
        # Determine activity type
        if not activity_type:
            if any(word in activity_lower for word in ["temple", "church", "mosque", "shrine", "religious"]):
                activity_type = "temple"
            elif any(word in activity_lower for word in ["fort", "castle", "ruins", "historical"]):
                activity_type = "fort"
            elif any(word in activity_lower for word in ["beach", "coast", "sea", "ocean"]):
                activity_type = "beach"
            elif any(word in activity_lower for word in ["market", "bazaar", "shopping"]):
                activity_type = "market"
            elif any(word in activity_lower for word in ["park", "safari", "wildlife", "nature"]):
                activity_type = "national_park"
            else:
                activity_type = "general"
        
        tips = self.cultural_tips.get(activity_type, {
            "dress_code": "Dress modestly and comfortably for the activity",
            "behavior": "Be respectful of local customs and traditions",
            "timing": "Check local opening hours and best visiting times",
            "safety": "Follow general safety guidelines and local advice"
        })
        
        return {
            "activity": activity_name,
            "location": location,
            "activity_type": activity_type,
            "cultural_tips": tips,
            "safety_reminders": random.sample(self.safety_tips["crowded_areas"], 2),
            "local_etiquette": self._get_local_etiquette(location),
            "special_notes": self._get_special_notes(activity_name, location)
        }
    
    def _get_local_etiquette(self, location: str) -> List[str]:
        """Get location-specific etiquette tips."""
        location_lower = location.lower()
        
        if "kandy" in location_lower:
            return [
                "Remove shoes before entering the Temple of the Tooth",
                "Dress conservatively when visiting religious sites",
                "Be respectful during Puja ceremonies"
            ]
        elif "anuradhapura" in location_lower or "polonnaruwa" in location_lower:
            return [
                "Remove shoes and hats at all archaeological sites",
                "Don't climb on ancient structures or stupas",
                "Be quiet and respectful in sacred areas"
            ]
        elif "galle" in location_lower:
            return [
                "Walk on the right side of the fort walls",
                "Be careful of uneven cobblestone paths",
                "Respect private property in the fort area"
            ]
        else:
            return [
                "Greet locals with a smile and 'Ayubowan'",
                "Use your right hand for giving and receiving",
                "Remove shoes when entering homes or temples"
            ]
    
    def _get_special_notes(self, activity_name: str, location: str) -> str:
        """Get special story-like tips for specific places."""
        activity_lower = activity_name.lower()
        
        if "sigiriya" in activity_lower:
            return "Climb early morning to avoid crowds and heat. The frescoes are best viewed in morning light. Take breaks on the way up - it's a challenging climb!"
        
        elif "temple of the tooth" in activity_lower:
            return "Visit during Puja times (6:30 AM, 9:30 AM, 6:30 PM) to witness the sacred ceremony. The golden casket is only shown during these times."
        
        elif "ella" in activity_lower and "train" in activity_lower:
            return "The Ella to Kandy train journey is one of the world's most scenic. Book a window seat on the right side for the best views of tea plantations and mountains."
        
        elif "yala" in activity_lower or "wilpattu" in activity_lower:
            return "Leopards are most active at dawn and dusk. Bring binoculars and a good camera. Listen to your guide - they know the animals' habits!"
        
        elif "galle fort" in activity_lower:
            return "Walk the ramparts at sunset for stunning ocean views. The fort comes alive in the evening with cafes and street performers. Perfect for photography!"
        
        else:
            return f"Take your time to explore {activity_name}. The best experiences often come from unexpected discoveries and conversations with locals."

    def enhance_activities_with_cultural_tips(self, daily_plan: DayPlan) -> DayPlan:
        """Enhance all activities in a daily plan with cultural tips."""
        enhanced_activities = []
        
        for activity in daily_plan.activities:
            cultural_tips = self.get_cultural_tips(activity.name, daily_plan.base_city)
            
            # Add cultural tips to activity
            activity_dict = activity.model_dump()
            activity_dict["cultural_tips"] = cultural_tips
            
            # Recreate activity with cultural tips
            enhanced_activity = Activity(**activity_dict)
            enhanced_activities.append(enhanced_activity)
        
        # Update daily plan
        daily_plan.activities = enhanced_activities
        return daily_plan

    def get_general_safety_tips(self, location: str) -> Dict[str, Any]:
        """Get general safety tips for a location."""
        return {
            "location": location,
            "emergency_numbers": {
                "police": "119",
                "ambulance": "110",
                "fire": "110",
                "tourist_police": "+94 11 242 1052"
            },
            "safety_tips": {
                "general": self.safety_tips["crowded_areas"],
                "transportation": self.safety_tips["transportation"],
                "food_safety": self.safety_tips["food_safety"]
            },
            "local_contacts": {
                "tourist_information": "Visit nearest tourist information center",
                "hotel_concierge": "Ask your hotel for local recommendations and safety advice"
            }
        }
