# src/tools/unsplash_images.py
"""
Unsplash Images - Fetches high-quality images for places using Unsplash API.
"""
import requests
import json
from typing import List, Dict, Any, Optional
from settings import HTTP_TIMEOUT

# Unsplash API credentials
UNSPLASH_ACCESS_KEY = "xEMYv_V9oFT_zIQgZ7BovwFbHrLKNaVWmXeiCxpJEuM"
UNSPLASH_SECRET_KEY = "f3ISG1t9oyuWHIeB0Pe8jutNYJvu4rditL5ZOFK13MQ"

def get_place_image(place_name: str, location: str = "", width: int = 800, height: int = 600) -> Optional[Dict[str, Any]]:
    """
    Get a high-quality image for a place from Unsplash.
    
    Args:
        place_name: Name of the place
        location: Location context (e.g., "Sri Lanka", "Galle")
        width: Image width
        height: Image height
    
    Returns:
        Dict with image URL and metadata, or None if not found
    """
    try:
        # Search for images related to the place
        search_query = f"{place_name} {location}".strip()
        
        url = "https://api.unsplash.com/search/photos"
        headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
        }
        params = {
            "query": search_query,
            "per_page": 5,
            "orientation": "landscape"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("results"):
            # Get the first result
            photo = data["results"][0]
            
            # Construct the image URL with desired dimensions
            image_url = f"{photo['urls']['regular']}&w={width}&h={height}&fit=crop"
            
            return {
                "url": image_url,
                "alt": photo.get("alt_description", place_name),
                "photographer": photo["user"]["name"],
                "photographer_url": photo["user"]["links"]["html"],
                "unsplash_url": photo["links"]["html"],
                "width": width,
                "height": height
            }
        
        return None
        
    except Exception as e:
        print(f"Unsplash API error for {place_name}: {e}")
        return None

def get_multiple_place_images(places: List[str], location: str = "") -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Get images for multiple places.
    
    Args:
        places: List of place names
        location: Location context
    
    Returns:
        Dict mapping place names to their image data
    """
    images = {}
    for place in places:
        images[place] = get_place_image(place, location)
    return images

def get_sri_lanka_place_image(place_name: str) -> Optional[Dict[str, Any]]:
    """
    Get an image for a Sri Lankan place.
    
    Args:
        place_name: Name of the place
    
    Returns:
        Dict with image URL and metadata
    """
    return get_place_image(place_name, "Sri Lanka")
