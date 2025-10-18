"""
Weather-Aware Planner Agent

This agent intelligently adapts activities based on weather conditions.
- Avoids beaches during rain
- Recommends indoor activities during bad weather
- Suggests weather-appropriate alternatives
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from contracts import Activity, DayPlan
from .weather_food_agent import get_weather_forecast


def get_weather_appropriate_activities(weather_condition: str, original_activities: List[Activity], 
                                     location: str) -> List[Activity]:
    """
    Get weather-appropriate activities based on current weather conditions.
    """
    weather_appropriate_activities = []
    
    for activity in original_activities:
        # Check if activity is weather-sensitive
        if activity.kind in ["beach", "outdoor", "hiking", "water_sports"]:
            if weather_condition in ["rainy", "cloudy", "light_rain"]:
                # Replace outdoor activities with indoor alternatives
                alternative = get_indoor_alternative(activity, location)
                if alternative:
                    weather_appropriate_activities.append(alternative)
                else:
                    # Keep original but add weather warning
                    activity.weather_warning = f"⚠️ Outdoor activity - check weather conditions"
                    weather_appropriate_activities.append(activity)
            else:
                # Good weather - keep outdoor activities
                weather_appropriate_activities.append(activity)
        else:
            # Indoor activities are fine in any weather
            weather_appropriate_activities.append(activity)
    
    return weather_appropriate_activities


def get_indoor_alternative(original_activity: Activity, location: str) -> Optional[Activity]:
    """
    Get indoor alternative for outdoor activities based on weather.
    """
    alternatives = {
        "beach": {
            "indoor_activities": ["museum", "cultural", "spa", "shopping", "restaurant"],
            "suggestions": [
                "Visit local museums and cultural sites",
                "Enjoy spa treatments and wellness",
                "Explore local markets and shopping",
                "Try local restaurants and cafes"
            ]
        },
        "outdoor": {
            "indoor_activities": ["museum", "cultural", "spa", "shopping"],
            "suggestions": [
                "Visit cultural attractions",
                "Enjoy indoor entertainment",
                "Explore local markets"
            ]
        },
        "hiking": {
            "indoor_activities": ["museum", "cultural", "spa"],
            "suggestions": [
                "Visit cultural sites",
                "Enjoy spa treatments",
                "Explore local history"
            ]
        },
        "water_sports": {
            "indoor_activities": ["spa", "cultural", "shopping"],
            "suggestions": [
                "Enjoy spa treatments",
                "Visit cultural attractions",
                "Explore local markets"
            ]
        }
    }
    
    if original_activity.kind in alternatives:
        alt_info = alternatives[original_activity.kind]
        # Create alternative activity
        alternative = Activity(
            name=f"Weather Alternative: {alt_info['suggestions'][0]}",
            kind=alt_info["indoor_activities"][0],
            start=original_activity.start,
            duration_min=original_activity.duration_min,
            poi_id=None,
            lat=original_activity.lat,
            lon=original_activity.lon,
            types=["tourist_attraction"],
            rating=None,
            user_ratings_total=None,
            weather_info={
                "location": location,
                "summary": f"Weather alternative for {original_activity.name}",
                "condition": "indoor",
                "note": f"Original activity: {original_activity.name} (outdoor)"
            }
        )
        return alternative
    
    return None


def add_weather_recommendations(day_plan: DayPlan) -> DayPlan:
    """
    Add weather-based recommendations to a day plan.
    """
    # Get weather for the day
    weather = get_weather_forecast(day_plan.base_city, str(day_plan.date))
    weather_condition = weather.get("condition", "unknown")
    
    # Get weather-appropriate activities
    weather_appropriate_activities = get_weather_appropriate_activities(
        weather_condition, day_plan.activities, day_plan.base_city
    )
    
    # Add weather recommendations to notes
    weather_notes = []
    if weather_condition in ["rainy", "cloudy", "light_rain"]:
        weather_notes.append(f"🌧️ Rainy weather - indoor activities recommended")
        weather_notes.append(f"☔ Bring umbrella and rain gear")
    elif weather_condition in ["sunny", "clear"]:
        weather_notes.append(f"☀️ Perfect weather for outdoor activities")
        weather_notes.append(f"🧴 Don't forget sunscreen and water")
    elif weather_condition == "partly_cloudy":
        weather_notes.append(f"⛅ Partly cloudy - good for most activities")
        weather_notes.append(f"🌤️ Weather may change - be prepared")
    
    # Update day plan
    updated_notes = day_plan.notes + weather_notes
    updated_day_plan = DayPlan(
        date=day_plan.date,
        base_city=day_plan.base_city,
        weather_hint=weather_condition,
        activities=weather_appropriate_activities,
        travel_legs=day_plan.travel_legs,
        notes=updated_notes
    )
    
    return updated_day_plan


class WeatherAwarePlanner:
    """
    Agent that intelligently adapts travel plans based on weather conditions.
    """
    
    def adapt_itinerary_to_weather(self, itinerary_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt an entire itinerary based on weather conditions.
        """
        adapted_daily_plan = []
        
        for day_data in itinerary_data.get("daily_plan", []):
            # Convert to DayPlan object
            activities = []
            for act_data in day_data.get("activities", []):
                activity = Activity(**act_data)
                activities.append(activity)
            
            day_plan = DayPlan(
                date=day_data["date"],
                base_city=day_data["base_city"],
                weather_hint=day_data.get("weather_hint"),
                activities=activities,
                travel_legs=day_data.get("travel_legs", []),
                notes=day_data.get("notes", [])
            )
            
            # Adapt to weather
            adapted_day = add_weather_recommendations(day_plan)
            
            # Convert back to dict
            adapted_day_data = {
                "date": adapted_day.date,
                "base_city": adapted_day.base_city,
                "weather_hint": adapted_day.weather_hint,
                "activities": [activity.model_dump(by_alias=True, mode="json") for activity in adapted_day.activities],
                "travel_legs": adapted_day.travel_legs,
                "notes": adapted_day.notes
            }
            
            adapted_daily_plan.append(adapted_day_data)
        
        # Update itinerary
        adapted_itinerary = itinerary_data.copy()
        adapted_itinerary["daily_plan"] = adapted_daily_plan
        
        return adapted_itinerary
