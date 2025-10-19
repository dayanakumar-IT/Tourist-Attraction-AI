"""
Train Booking Agent - Integrates with Sri Lanka Railways for train routes,
schedules, and booking information.
"""

from typing import Dict, List, Any, Optional, Tuple
import requests
import json
from datetime import datetime, timedelta

class TrainBookingAgent:
    def __init__(self):
        self.railway_api_base = "https://seatreservation.railway.gov.lk/mtktwebslr/"
        self.station_mapping = {
            "colombo": "Colombo Fort",
            "galle": "Galle",
            "kandy": "Kandy",
            "anuradhapura": "Anuradhapura",
            "jaffna": "Jaffna",
            "trincomalee": "Trincomalee",
            "batticaloa": "Batticaloa",
            "ella": "Ella",
            "badulla": "Badulla",
            "matara": "Matara",
            "kurunegala": "Kurunegala",
            "polonnaruwa": "Polonnaruwa",
            "sigiriya": "Habarana",  # Closest station to Sigiriya
            "nuwara eliya": "Nanu Oya",
            "negombo": "Negombo"
        }
        
        # Popular train routes with approximate distances and durations
        self.train_routes = {
            "colombo-galle": {
                "distance_km": 116,
                "duration_hours": 2.5,
                "frequency": "Every 30 minutes",
                "classes": ["First Class", "Second Class", "Third Class"],
                "scenic_rating": 8,
                "booking_link": "https://seatreservation.railway.gov.lk/mtktwebslr/"
            },
            "colombo-kandy": {
                "distance_km": 120,
                "duration_hours": 3,
                "frequency": "Every hour",
                "classes": ["First Class", "Second Class", "Third Class"],
                "scenic_rating": 9,
                "booking_link": "https://seatreservation.railway.gov.lk/mtktwebslr/"
            },
            "kandy-ella": {
                "distance_km": 150,
                "duration_hours": 7,
                "frequency": "Daily (morning departure)",
                "classes": ["First Class", "Second Class", "Third Class"],
                "scenic_rating": 10,
                "booking_link": "https://seatreservation.railway.gov.lk/mtktwebslr/"
            },
            "colombo-anuradhapura": {
                "distance_km": 200,
                "duration_hours": 4,
                "frequency": "Daily",
                "classes": ["First Class", "Second Class", "Third Class"],
                "scenic_rating": 6,
                "booking_link": "https://seatreservation.railway.gov.lk/mtktwebslr/"
            },
            "colombo-jaffna": {
                "distance_km": 400,
                "duration_hours": 8,
                "frequency": "Daily",
                "classes": ["First Class", "Second Class", "Third Class"],
                "scenic_rating": 7,
                "booking_link": "https://seatreservation.railway.gov.lk/mtktwebslr/"
            }
        }

    def get_train_route(self, from_city: str, to_city: str) -> Optional[Dict[str, Any]]:
        """Get train route information between two cities."""
        from_station = self._get_station_name(from_city)
        to_station = self._get_station_name(to_city)
        
        if not from_station or not to_station:
            return None
        
        route_key = f"{from_city.lower()}-{to_city.lower()}"
        reverse_route_key = f"{to_city.lower()}-{from_city.lower()}"
        
        route_info = self.train_routes.get(route_key) or self.train_routes.get(reverse_route_key)
        
        if not route_info:
            return None
        
        return {
            "from_station": from_station,
            "to_station": to_station,
            "from_city": from_city,
            "to_city": to_city,
            "distance_km": route_info["distance_km"],
            "duration_hours": route_info["duration_hours"],
            "frequency": route_info["frequency"],
            "available_classes": route_info["classes"],
            "scenic_rating": route_info["scenic_rating"],
            "booking_url": route_info["booking_link"],
            "recommendations": self._get_train_recommendations(route_key, route_info)
        }

    def _get_station_name(self, city: str) -> Optional[str]:
        """Get railway station name for a city."""
        return self.station_mapping.get(city.lower())

    def _get_train_recommendations(self, route_key: str, route_info: Dict) -> List[str]:
        """Get specific recommendations for train routes."""
        recommendations = []
        
        if route_key == "kandy-ella":
            recommendations = [
                "Book window seats on the right side for best mountain views",
                "Bring snacks and water for the 7-hour journey",
                "Departure is usually 8:47 AM from Kandy",
                "Consider First Class for more comfort on this scenic route"
            ]
        elif route_key == "colombo-galle":
            recommendations = [
                "Coastal route with beautiful ocean views",
                "Frequent departures every 30 minutes",
                "Good for day trips from Colombo",
                "Second Class offers good value for money"
            ]
        elif route_key == "colombo-kandy":
            recommendations = [
                "Hill country route with tea plantation views",
                "Air-conditioned First Class available",
                "Good for visiting Kandy and surrounding areas",
                "Book in advance during peak season"
            ]
        else:
            recommendations = [
                "Check departure times in advance",
                "Arrive at station 30 minutes before departure",
                "Bring valid ID for ticket collection"
            ]
        
        return recommendations

    def get_train_pricing(self, route_info: Dict[str, Any], passenger_count: int = 1) -> Dict[str, Any]:
        """Get estimated train pricing for a route."""
        # Approximate pricing in LKR (these would be fetched from actual API)
        base_prices = {
            "First Class": 500,
            "Second Class": 300,
            "Third Class": 150
        }
        
        pricing = {}
        for class_type in route_info.get("available_classes", []):
            base_price = base_prices.get(class_type, 200)
            # Add distance-based pricing
            distance_factor = route_info.get("distance_km", 100) / 100
            price_per_person = int(base_price * distance_factor)
            
            pricing[class_type] = {
                "price_per_person_lkr": price_per_person,
                "total_price_lkr": price_per_person * passenger_count,
                "currency": "LKR"
            }
        
        return {
            "route": f"{route_info['from_city']} to {route_info['to_city']}",
            "pricing": pricing,
            "booking_url": route_info.get("booking_url"),
            "note": "Prices are approximate. Check official website for current rates."
        }

    def suggest_train_alternatives(self, from_city: str, to_city: str) -> List[Dict[str, Any]]:
        """Suggest train alternatives for a route."""
        alternatives = []
        
        # Check for direct routes
        direct_route = self.get_train_route(from_city, to_city)
        if direct_route:
            alternatives.append({
                "type": "direct",
                "route": direct_route,
                "description": f"Direct train from {from_city} to {to_city}"
            })
        
        # Check for connecting routes through major hubs
        major_hubs = ["colombo", "kandy", "anuradhapura"]
        
        for hub in major_hubs:
            if hub not in [from_city.lower(), to_city.lower()]:
                route1 = self.get_train_route(from_city, hub)
                route2 = self.get_train_route(hub, to_city)
                
                if route1 and route2:
                    total_duration = route1["duration_hours"] + route2["duration_hours"] + 1  # 1 hour connection time
                    alternatives.append({
                        "type": "connecting",
                        "route": f"{from_city} → {hub} → {to_city}",
                        "total_duration_hours": total_duration,
                        "legs": [route1, route2],
                        "description": f"Connecting via {hub.title()}"
                    })
        
        return alternatives

    def get_scenic_train_routes(self) -> List[Dict[str, Any]]:
        """Get list of scenic train routes in Sri Lanka."""
        scenic_routes = []
        
        for route_key, route_info in self.train_routes.items():
            if route_info["scenic_rating"] >= 8:  # Highly scenic routes
                scenic_routes.append({
                    "route": route_key.replace("-", " to ").title(),
                    "scenic_rating": route_info["scenic_rating"],
                    "duration_hours": route_info["duration_hours"],
                    "description": self._get_scenic_description(route_key),
                    "booking_url": route_info["booking_link"]
                })
        
        return sorted(scenic_routes, key=lambda x: x["scenic_rating"], reverse=True)

    def _get_scenic_description(self, route_key: str) -> str:
        """Get scenic description for a route."""
        descriptions = {
            "kandy-ella": "World-famous scenic railway through tea plantations and mountains. Considered one of the most beautiful train journeys in the world.",
            "colombo-kandy": "Hill country route with stunning views of tea plantations, waterfalls, and mountain landscapes.",
            "colombo-galle": "Coastal railway with beautiful ocean views and glimpses of traditional fishing villages."
        }
        
        return descriptions.get(route_key, "Scenic railway route with beautiful Sri Lankan landscapes.")

    def enhance_transport_with_train_options(self, travel_legs: List[Dict], from_city: str, to_city: str) -> List[Dict]:
        """Enhance transport legs with train options."""
        train_route = self.get_train_route(from_city, to_city)
        
        if train_route:
            train_leg = {
                "mode": "train",
                "from": from_city,
                "to": to_city,
                "distance_km": train_route["distance_km"],
                "duration_hours": train_route["duration_hours"],
                "scenic_rating": train_route["scenic_rating"],
                "booking_url": train_route["booking_url"],
                "recommendations": train_route["recommendations"],
                "available_classes": train_route["available_classes"],
                "frequency": train_route["frequency"],
                "estimated_cost": self._estimate_train_cost(train_route),
                "cost_currency": "LKR"
            }
            
            # Add train option to existing transport legs
            travel_legs.append(train_leg)
        
        return travel_legs

    def _estimate_train_cost(self, route_info: Dict) -> int:
        """Estimate train cost based on route."""
        base_cost = 200
        distance_factor = route_info.get("distance_km", 100) / 100
        return int(base_cost * distance_factor)
