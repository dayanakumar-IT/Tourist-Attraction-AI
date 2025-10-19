# src/tools/sri_lanka_places.py
"""
Real Sri Lankan places database for when Google Places API is unavailable.
"""

SRI_LANKA_PLACES = {
    "beach": [
        {
            "name": "Unawatuna Beach",
            "lat": 6.0167,
            "lon": 80.2500,
            "rating": 4.5,
            "description": "Famous golden beach with coral reefs and clear waters"
        },
        {
            "name": "Mirissa Beach",
            "lat": 5.9500,
            "lon": 80.4500,
            "rating": 4.6,
            "description": "Perfect for whale watching and surfing"
        },
        {
            "name": "Bentota Beach",
            "lat": 6.4167,
            "lon": 80.0000,
            "rating": 4.4,
            "description": "Long sandy beach with water sports"
        },
        {
            "name": "Arugam Bay",
            "lat": 6.8333,
            "lon": 81.8333,
            "rating": 4.7,
            "description": "World-class surfing destination"
        },
        {
            "name": "Hikkaduwa Beach",
            "lat": 6.1333,
            "lon": 80.1000,
            "rating": 4.3,
            "description": "Coral reef and marine sanctuary"
        }
    ],
    "culture": [
        {
            "name": "Temple of the Sacred Tooth Relic",
            "lat": 7.2944,
            "lon": 80.6414,
            "rating": 4.8,
            "description": "Most sacred Buddhist temple in Sri Lanka"
        },
        {
            "name": "Sigiriya Rock Fortress",
            "lat": 7.9569,
            "lon": 80.7597,
            "rating": 4.9,
            "description": "Ancient rock fortress and UNESCO World Heritage site"
        },
        {
            "name": "Dambulla Cave Temple",
            "lat": 7.8567,
            "lon": 80.6519,
            "rating": 4.7,
            "description": "Largest and best-preserved cave temple complex"
        },
        {
            "name": "Galle Fort",
            "lat": 6.0267,
            "lon": 80.2167,
            "rating": 4.6,
            "description": "Historic Dutch colonial fort and UNESCO site"
        },
        {
            "name": "Anuradhapura Ancient City",
            "lat": 8.3111,
            "lon": 80.4031,
            "rating": 4.8,
            "description": "Ancient capital with sacred Bodhi tree"
        }
    ],
    "wildlife": [
        {
            "name": "Yala National Park",
            "lat": 6.3722,
            "lon": 81.5250,
            "rating": 4.7,
            "description": "Best place to see leopards and elephants"
        },
        {
            "name": "Udawalawe National Park",
            "lat": 6.4333,
            "lon": 80.8833,
            "rating": 4.6,
            "description": "Elephant sanctuary with guaranteed sightings"
        },
        {
            "name": "Minneriya National Park",
            "lat": 7.9167,
            "lon": 80.9167,
            "rating": 4.5,
            "description": "Famous for the elephant gathering"
        },
        {
            "name": "Sinharaja Forest Reserve",
            "lat": 6.4167,
            "lon": 80.5000,
            "rating": 4.8,
            "description": "UNESCO World Heritage rainforest"
        },
        {
            "name": "Wilpattu National Park",
            "lat": 8.4500,
            "lon": 80.0000,
            "rating": 4.4,
            "description": "Largest national park with natural lakes"
        }
    ],
    "adventure": [
        {
            "name": "Ella Rock",
            "lat": 6.8667,
            "lon": 81.0500,
            "rating": 4.6,
            "description": "Challenging hike with panoramic views"
        },
        {
            "name": "Little Adam's Peak",
            "lat": 6.8500,
            "lon": 81.0500,
            "rating": 4.5,
            "description": "Easier hike with stunning sunrise views"
        },
        {
            "name": "World's End - Horton Plains",
            "lat": 6.8000,
            "lon": 80.8000,
            "rating": 4.7,
            "description": "Dramatic cliff edge at 2000m elevation"
        },
        {
            "name": "Pidurangala Rock",
            "lat": 7.9667,
            "lon": 80.7500,
            "rating": 4.4,
            "description": "Alternative viewpoint to Sigiriya"
        },
        {
            "name": "Bambarakanda Falls",
            "lat": 6.7500,
            "lon": 80.9167,
            "rating": 4.3,
            "description": "Highest waterfall in Sri Lanka"
        }
    ],
    "nature": [
        {
            "name": "Nuwara Eliya",
            "lat": 6.9667,
            "lon": 80.7667,
            "rating": 4.5,
            "description": "Hill station with tea plantations and cool climate"
        },
        {
            "name": "Kandy Lake",
            "lat": 7.2944,
            "lon": 80.6414,
            "rating": 4.3,
            "description": "Artificial lake in the heart of Kandy"
        },
        {
            "name": "Royal Botanical Gardens - Peradeniya",
            "lat": 7.2667,
            "lon": 80.6000,
            "rating": 4.6,
            "description": "Beautiful botanical gardens with rare plants"
        },
        {
            "name": "Knuckles Mountain Range",
            "lat": 7.4000,
            "lon": 80.8000,
            "rating": 4.7,
            "description": "UNESCO World Heritage mountain range"
        },
        {
            "name": "Horton Plains National Park",
            "lat": 6.8000,
            "lon": 80.8000,
            "rating": 4.8,
            "description": "Highland national park with unique ecosystem"
        }
    ],
    "food": [
        {
            "name": "Ministry of Crab",
            "lat": 6.9167,
            "lon": 79.8500,
            "rating": 4.8,
            "description": "Award-winning restaurant specializing in Sri Lankan crab"
        },
        {
            "name": "Paradise Road Tintagel Colombo",
            "lat": 6.9167,
            "lon": 79.8500,
            "rating": 4.6,
            "description": "Fine dining in a colonial mansion"
        },
        {
            "name": "Upali's by Nawaloka",
            "lat": 6.9167,
            "lon": 79.8500,
            "rating": 4.4,
            "description": "Authentic Sri Lankan cuisine"
        },
        {
            "name": "Curry Leaf - Mount Lavinia",
            "lat": 6.8333,
            "lon": 79.8667,
            "rating": 4.5,
            "description": "Beachfront dining with local flavors"
        },
        {
            "name": "The Empire Cafe",
            "lat": 6.9167,
            "lon": 79.8500,
            "rating": 4.3,
            "description": "Colonial-style cafe with Sri Lankan breakfast"
        }
    ]
}

def get_real_sri_lanka_places(theme: str, base_city: str, limit: int = 5) -> list:
    """Get real Sri Lankan places for a given theme."""
    places = SRI_LANKA_PLACES.get(theme, [])
    
    # Filter by proximity to base city if possible
    city_coords = {
        "colombo": (6.9271, 79.8612),
        "kandy": (7.2906, 80.6337),
        "galle": (6.0329, 80.2170),
        "anuradhapura": (8.3111, 80.4031),
        "jaffna": (9.6615, 80.0255),
        "trincomalee": (8.5874, 81.2152),
        "batticaloa": (7.7102, 81.6924),
        "negombo": (7.2086, 79.8358),
        "ella": (6.8667, 81.0500),
        "nuwara eliya": (6.9667, 80.7667)
    }
    
    base_coords = city_coords.get(base_city.lower(), (6.9271, 79.8612))
    
    # Sort by rating and return top places
    sorted_places = sorted(places, key=lambda x: x["rating"], reverse=True)
    
    # Add some variety by mixing high-rated places
    result = []
    for i, place in enumerate(sorted_places[:limit]):
        result.append({
            "name": place["name"],
            "point": {"lat": place["lat"], "lon": place["lon"]},
            "rating": place["rating"],
            "description": place["description"],
            "xid": f"sri_lanka_{theme}_{i}",
            "kinds": [theme],
            "types": [theme, "tourist_attraction"]
        })
    
    return result
