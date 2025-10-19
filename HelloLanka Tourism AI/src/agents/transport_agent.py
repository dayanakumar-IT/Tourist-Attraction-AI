# src/agents/transport_agent.py
"""
TransportAgent - Handles transportation optimization and routing.
"""
import json
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import time, timedelta
from settings import GOOGLE_PLACES_API_KEY, HTTP_TIMEOUT
from contracts import TravelLeg, Activity


def _call_google_maps_api(params: Dict[str, Any], endpoint: str = "directions") -> Dict[str, Any]:
    """Make a call to Google Maps API with error handling."""
    if not GOOGLE_PLACES_API_KEY:
        raise RuntimeError("GOOGLE_PLACES_API_KEY is missing; cannot fetch routing data.")
    
    # Use different endpoints based on the type of request
    if endpoint == "directions":
        url = "https://maps.googleapis.com/maps/api/directions/json"
    elif endpoint == "distance_matrix":
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    else:
        url = "https://maps.googleapis.com/maps/api/directions/json"
    
    params["key"] = GOOGLE_PLACES_API_KEY
    
    try:
        response = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Google Maps API call failed: {str(e)}")


def get_route_info(origin: str, destination: str, mode: str = "driving") -> Dict[str, Any]:
    """
    Get route information between two locations using Google Maps API.
    
    Args:
        origin: Starting location
        destination: Destination location
        mode: Transportation mode (driving, walking, transit)
    
    Returns:
        Dict with route information
    """
    try:
        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "units": "metric",
            "region": "lk"  # Sri Lanka
        }
        
        result = _call_google_maps_api(params, "directions")
        
        if result.get("status") != "OK" or not result.get("routes"):
            return {
                "origin": origin,
                "destination": destination,
                "mode": mode,
                "duration_min": 30,  # Default fallback
                "distance_km": 5.0,  # Default fallback
                "eta": "30 min",
                "error": "No route found"
            }
        
        route = result["routes"][0]
        leg = route["legs"][0]
        
        duration_seconds = leg["duration"]["value"]
        duration_min = duration_seconds // 60
        distance_meters = leg["distance"]["value"]
        distance_km = distance_meters / 1000
        
        return {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "duration_min": duration_min,
            "distance_km": round(distance_km, 1),
            "eta": f"{duration_min} min",
            "route_summary": leg.get("summary", ""),
            "instructions": [step["html_instructions"] for step in leg.get("steps", [])]
        }
        
    except Exception as e:
        # Return default route info if API fails
        return {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "duration_min": 30,
            "distance_km": 5.0,
            "eta": "30 min",
            "error": str(e)
        }


def get_transport_cost(origin: str, destination: str, mode: str = "driving") -> Dict[str, Any]:
    """
    Get transport cost estimation using Google Distance Matrix API.
    
    Args:
        origin: Starting location
        destination: Destination location
        mode: Transportation mode (driving, walking, transit)
    
    Returns:
        Dict with cost estimation
    """
    try:
        # First get distance and duration
        route_info = get_route_info(origin, destination, mode)
        distance_km = route_info.get("distance_km", 0)
        
        # Estimate cost based on mode and distance
        print(f"DEBUG: Estimating cost for {mode}, distance: {distance_km} km")
        if mode == "walking":
            estimated_cost = 0  # Free
        elif mode == "driving":
            # Estimate: 50 LKR per km for fuel + 20 LKR per km for maintenance
            estimated_cost = int(distance_km * 70)
        elif mode == "tuk":
            # Estimate: 100 LKR per km for tuk-tuk
            estimated_cost = int(distance_km * 100)
        elif mode == "bus":
            # Estimate: 20 LKR per km for bus
            estimated_cost = int(distance_km * 20)
        else:
            estimated_cost = int(distance_km * 50)  # Default rate
        
        print(f"DEBUG: Calculated cost: {estimated_cost} LKR")
        
        return {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "estimated_cost": estimated_cost,
            "cost_currency": "LKR",
            "distance_km": distance_km
        }
        
    except Exception as e:
        # Fallback cost estimation
        return {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "estimated_cost": 1000,  # Default fallback cost
            "cost_currency": "LKR",
            "error": str(e)
        }


def recommend_transport_mode(distance_km: float, group_size: int, budget_currency: str) -> str:
    """
    Recommend the best transportation mode based on distance, group size, and budget.
    
    Args:
        distance_km: Distance in kilometers
        group_size: Number of people
        budget_currency: Currency code (USD, LKR, etc.)
    
    Returns:
        Recommended transport mode
    """
    if distance_km < 1.0:
        return "walk"
    elif distance_km < 5.0:
        if group_size <= 2:
            return "tuk"
        else:
            return "car"
    elif distance_km < 20.0:
        if group_size <= 4:
            return "car"
        else:
            return "car"  # Multiple cars or van
    else:
        return "car"


def estimate_transport_cost(mode: str, distance_km: float, group_size: int, currency: str) -> float:
    """
    Estimate transportation cost based on mode, distance, and group size.
    
    Args:
        mode: Transportation mode
        distance_km: Distance in kilometers
        group_size: Number of people
        currency: Currency code
    
    Returns:
        Estimated cost in the specified currency
    """
    # Base rates in LKR (Sri Lankan Rupees)
    rates_lkr = {
        "walk": 0,
        "tuk": 50,  # LKR per km
        "car": 100,  # LKR per km (including fuel)
        "train": 20,  # LKR per km
        "bus": 15   # LKR per km
    }
    
    base_rate = rates_lkr.get(mode, 100)
    base_cost = base_rate * distance_km
    
    # Adjust for group size
    if mode == "tuk" and group_size > 2:
        base_cost *= 1.5  # Need multiple tuk-tuks
    elif mode == "car" and group_size > 4:
        base_cost *= 1.8  # Need larger vehicle
    
    # Convert to requested currency (simplified)
    if currency.upper() == "USD":
        return round(base_cost / 300, 2)  # Approximate LKR to USD
    elif currency.upper() == "EUR":
        return round(base_cost / 330, 2)  # Approximate LKR to EUR
    else:
        return round(base_cost, 2)  # Return in LKR


class TransportAgent:
    """
    Agent that optimizes transportation between activities and locations.
    """
    
    def optimize_day_transport(self, activities: List[Activity], base_city: str, 
                              group_size: int = 1, budget_currency: str = "LKR") -> List[TravelLeg]:
        """
        Optimize transportation for a day's activities.
        
        Args:
            activities: List of activities for the day
            base_city: Base city for the day
            group_size: Number of people
            budget_currency: Currency for cost estimation
        
        Returns:
            List of optimized travel legs
        """
        if len(activities) < 1:
            return []
        
        travel_legs = []
        current_location = base_city
        
        for i, activity in enumerate(activities):
            if i == 0:
                # First activity - travel from base city
                if activity.lat and activity.lon:
                    destination = f"{activity.lat},{activity.lon}"
                else:
                    destination = activity.name
                
                # Get route info
                route_info = get_route_info(current_location, destination)
                
                # Recommend transport mode
                recommended_mode = recommend_transport_mode(
                    route_info["distance_km"], 
                    group_size, 
                    budget_currency
                )
                
                # Get cost estimation using Google Distance Matrix
                cost_info = get_transport_cost(current_location, destination, recommended_mode)
                cost = cost_info.get("estimated_cost", 0)
                
                # Create travel leg
                travel_leg = TravelLeg(
                    mode=recommended_mode,
                    from_=current_location,
                    to=activity.name,
                    eta_min=route_info["duration_min"],
                    km=route_info["distance_km"],
                    estimated_cost=cost,
                    cost_currency=budget_currency
                )
                
                # Add cost information as additional attribute
                travel_leg.estimated_cost = cost
                travel_leg.cost_currency = budget_currency
                
                travel_legs.append(travel_leg)
                current_location = activity.name
            
            else:
                # Travel between activities
                prev_activity = activities[i-1]
                if activity.lat and activity.lon and prev_activity.lat and prev_activity.lon:
                    origin = f"{prev_activity.lat},{prev_activity.lon}"
                    destination = f"{activity.lat},{activity.lon}"
                else:
                    origin = prev_activity.name
                    destination = activity.name
                
                # Get route info
                route_info = get_route_info(origin, destination)
                
                # Recommend transport mode
                recommended_mode = recommend_transport_mode(
                    route_info["distance_km"], 
                    group_size, 
                    budget_currency
                )
                
                # Get cost estimation using Google Distance Matrix
                cost_info = get_transport_cost(current_location, destination, recommended_mode)
                cost = cost_info.get("estimated_cost", 0)
                
                # Create travel leg
                travel_leg = TravelLeg(
                    mode=recommended_mode,
                    from_=prev_activity.name,
                    to=activity.name,
                    eta_min=route_info["duration_min"],
                    km=route_info["distance_km"],
                    estimated_cost=cost,
                    cost_currency=budget_currency
                )
                
                travel_legs.append(travel_leg)
        
        return travel_legs
    
    def optimize_itinerary_transport(self, itinerary_data: Dict[str, Any], 
                                   group_size: int = 1, budget_currency: str = "LKR") -> Dict[str, Any]:
        """
        Optimize transportation for an entire itinerary.
        
        Args:
            itinerary_data: Itinerary dictionary
            group_size: Number of people
            budget_currency: Currency for cost estimation
        
        Returns:
            Enhanced itinerary with optimized transportation
        """
        enhanced_daily_plan = []
        
        for day_data in itinerary_data.get("daily_plan", []):
            # Enhance existing travel legs with cost information
            enhanced_travel_legs = []
            for leg_data in day_data.get("travel_legs", []):
                # Get cost estimation for existing travel leg
                from_place = leg_data.get("from", leg_data.get("from_", ""))
                to_place = leg_data.get("to", "")
                mode = leg_data.get("mode", "driving")
                
                if from_place and to_place:
                    cost_info = get_transport_cost(from_place, to_place, mode)
                    estimated_cost = cost_info.get("estimated_cost", 0)
                    cost_currency = cost_info.get("cost_currency", budget_currency)
                    
                    # Enhance the existing leg with cost information
                    enhanced_leg = leg_data.copy()
                    enhanced_leg["estimated_cost"] = estimated_cost
                    enhanced_leg["cost_currency"] = cost_currency
                    enhanced_travel_legs.append(enhanced_leg)
                else:
                    # Keep original leg if we can't get cost info
                    enhanced_travel_legs.append(leg_data)
            
            # Update day data with enhanced transport
            enhanced_day = day_data.copy()
            enhanced_day["travel_legs"] = enhanced_travel_legs
            
            enhanced_daily_plan.append(enhanced_day)
        
        # Update itinerary with enhanced daily plans
        enhanced_itinerary = itinerary_data.copy()
        enhanced_itinerary["daily_plan"] = enhanced_daily_plan
        
        return enhanced_itinerary
