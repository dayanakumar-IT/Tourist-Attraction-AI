"""
Sri Lankan places with real coordinates for accurate mapping.
"""
from typing import Dict, Tuple, List

# Real coordinates for major Sri Lankan cities and attractions
SRI_LANKA_COORDINATES = {
    # Major Cities
    "colombo": (6.9271, 79.8612),
    "kandy": (7.2906, 80.6337),
    "galle": (6.0535, 80.2210),
    "jaffna": (9.6615, 80.0255),
    "anuradhapura": (8.3114, 80.4037),
    "trincomalee": (8.5874, 81.2152),
    "batticaloa": (7.7102, 81.6924),
    "negombo": (7.2086, 79.8356),
    "kurunegala": (7.4863, 80.3647),
    "ratnapura": (6.6828, 80.4012),
    
    # Popular Attractions
    "sigiriya": (7.9569, 80.7597),
    "polonnaruwa": (7.9403, 81.0188),
    "ella": (6.8667, 81.0467),
    "nuwara eliya": (6.9497, 80.7891),
    "mirissa": (5.9495, 80.4583),
    "unawatuna": (6.0103, 80.2500),
    "hikkaduwa": (6.1406, 80.1000),
    "bentota": (6.4211, 79.9956),
    "kalpitiya": (8.2500, 79.8333),
    "weligama": (5.9750, 80.4250),
    
    # Temples and Cultural Sites
    "temple of the sacred tooth relic": (7.2944, 80.6414),
    "gangaramaya temple": (6.9128, 79.8500),
    "nallur kandaswamy temple": (9.6615, 80.0255),
    "jaffna fort": (9.6615, 80.0255),
    "galle fort": (6.0535, 80.2210),
    "dambulla cave temple": (7.8567, 80.6517),
    "mihintale": (8.3500, 80.5167),
    "ruwanwelisaya": (8.3114, 80.4037),
    "jetavanaramaya": (8.3114, 80.4037),
    
    # National Parks
    "yala national park": (6.3729, 81.5204),
    "wilpattu national park": (8.4500, 80.0000),
    "udawalawe national park": (6.4333, 80.8833),
    "minneriya national park": (7.9167, 80.8333),
    "kumana national park": (6.5000, 81.6667),
    
    # Beaches
    "arugam bay": (6.8333, 81.8333),
    "pasikudah": (7.9167, 81.5833),
    "nilaveli": (8.7500, 81.1667),
    "trincomalee beach": (8.5874, 81.2152),
    "batticaloa beach": (7.7102, 81.6924),
}

def get_coordinates(place_name: str) -> Tuple[float, float]:
    """Get coordinates for a place name."""
    place_lower = place_name.lower().strip()
    
    # Direct match
    if place_lower in SRI_LANKA_COORDINATES:
        return SRI_LANKA_COORDINATES[place_lower]
    
    # Partial match for common variations
    for key, coords in SRI_LANKA_COORDINATES.items():
        if place_lower in key or key in place_lower:
            return coords
    
    # Default to Colombo if not found
    return SRI_LANKA_COORDINATES["colombo"]

def get_places_in_region(region: str) -> List[Dict[str, Tuple[float, float]]]:
    """Get all places in a specific region."""
    region_lower = region.lower()
    places = []
    
    for place, coords in SRI_LANKA_COORDINATES.items():
        if region_lower in place or place in region_lower:
            places.append({"name": place, "coordinates": coords})
    
    return places

def calculate_distance(place1: str, place2: str) -> float:
    """Calculate distance between two places in kilometers."""
    import math
    
    coords1 = get_coordinates(place1)
    coords2 = get_coordinates(place2)
    
    # Haversine formula
    R = 6371  # Earth's radius in kilometers
    lat1, lon1 = math.radians(coords1[0]), math.radians(coords1[1])
    lat2, lon2 = math.radians(coords2[0]), math.radians(coords2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def get_travel_time(place1: str, place2: str, mode: str = "car") -> int:
    """Get estimated travel time in minutes."""
    distance = calculate_distance(place1, place2)
    
    # Average speeds for different modes
    speeds = {
        "car": 50,      # km/h
        "train": 40,    # km/h
        "bus": 35,      # km/h
        "tuk": 30,      # km/h
        "walk": 5       # km/h
    }
    
    speed = speeds.get(mode, 50)
    time_hours = distance / speed
    return int(time_hours * 60)  # Convert to minutes
