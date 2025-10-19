import json, requests
from typing import List, Tuple, Dict, Any
from settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE

CONTROLLED = ["beach","spa","adventure","culture","nature","food","wellness","wildlife","photography","mixed_highlights"]

def _call_gemini_normalize(raws: List[str]) -> List[str]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing; cannot normalize themes with LLM.")

    url = GEMINI_BASE.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}

    prompt = (
        "You map arbitrary user travel interests to normalized themes from this fixed set: "
        f"{CONTROLLED}. Return ONLY a JSON list of themes (no prose, no explanation). "
        "If an input implies multiple themes, include all relevant ones."
    )

    user = ", ".join(raws)
    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]

    # Extract JSON array defensively
    start = content.find("[")
    end   = content.rfind("]")+1
    if start == -1 or end <= start:
        raise ValueError(f"Gemini returned unexpected content (no JSON array): {content!r}")

    parsed = json.loads(content[start:end])

    if not isinstance(parsed, list):
        raise ValueError(f"Gemini returned non-list: {parsed!r}")

    out = [t for t in parsed if t in CONTROLLED]
    if not out:
        raise ValueError(f"Gemini returned no valid themes from {parsed!r}")
    return out

def normalize_themes(themes_raw: List[str], free_text_interest: str|None) -> List[str]:
    raws = list(themes_raw or [])
    if free_text_interest:
        raws.append(free_text_interest)
    if not raws:
        return ["culture", "nature"]  # safe defaults instead of raising error
    
    try:
        return _call_gemini_normalize(raws)
    except Exception as e:
        print(f"LLM normalization failed: {e}, using intelligent fallback")
        # Enhanced fallback: map common keywords to themes with more intelligence
        fallback = []
        text = " ".join(raws).lower()
        
        # Beach and water activities
        if any(k in text for k in ["beach", "sea", "ocean", "coast", "swim", "surf", "diving", "snorkeling", "whale", "dolphin"]):
            fallback.append("beach")
        
        # Adventure and outdoor activities
        if any(k in text for k in ["mountain", "hill", "hike", "trek", "climb", "adventure", "outdoor", "camping", "rock", "waterfall"]):
            fallback.append("adventure")
        
        # Cultural and historical sites
        if any(k in text for k in ["temple", "church", "mosque", "religious", "spiritual", "ancient", "fort", "castle", "ruins", "historical", "heritage", "monument"]):
            fallback.append("culture")
        
        # Food and culinary experiences
        if any(k in text for k in ["food", "eat", "restaurant", "cuisine", "cooking", "spice", "curry", "tea", "coffee", "market", "street food"]):
            fallback.append("food")
        
        # Wildlife and nature
        if any(k in text for k in ["wildlife", "animal", "safari", "elephant", "bird", "leopard", "nature", "park", "forest", "jungle", "eco"]):
            fallback.append("wildlife")
        
        # Photography and scenic spots
        if any(k in text for k in ["photo", "picture", "camera", "instagram", "scenic", "view", "sunset", "sunrise", "landscape"]):
            fallback.append("photography")
        
        # Wellness and relaxation
        if any(k in text for k in ["spa", "massage", "yoga", "meditation", "relax", "wellness", "healing", "retreat"]):
            fallback.append("wellness")
        
        # Mixed experiences
        if any(k in text for k in ["everything", "all", "mixed", "variety", "diverse", "comprehensive", "complete"]):
            fallback.append("mixed_highlights")
        
        return fallback if fallback else ["culture", "nature"]

def infer_traveler_profile(currency: str, override: str|None) -> Tuple[str, str]:
    # This is a simple rule, not a price heuristic.
    if override in ("local_or_expat","foreign_tourist"):
        return override, "explicit_override"
    if currency.upper() != "LKR":
        return "foreign_tourist", "currency_inference"
    return "local_or_expat", "currency_inference"

def analyze_user_interests(user_input: str) -> Dict[str, Any]:
    """
    Analyze user input to extract interests and suggest places in Sri Lanka.
    Returns a dictionary with interests, places, and confidence score.
    """
    try:
        # First, normalize the themes from the user input
        interests = normalize_themes([], user_input)
        
        # Then, use LLM to suggest specific places based on interests
        places = _suggest_places_from_interests(interests, user_input)
        
        # Calculate confidence based on how many interests were detected
        confidence = min(len(interests) / 3.0, 1.0)  # Max confidence when 3+ interests detected
        
        return {
            "interests": interests,
            "places": places,
            "confidence": confidence
        }
    except Exception as e:
        print(f"Error in analyze_user_interests: {e}")
        # Fallback to basic analysis
        return {
            "interests": ["culture", "nature"],
            "places": [],
            "confidence": 0.5
        }

def _suggest_places_from_interests(interests: List[str], user_input: str) -> List[str]:
    """
    Use LLM to suggest specific places in Sri Lanka based on interests.
    """
    if not GEMINI_API_KEY:
        return _fallback_place_suggestions(interests)
    
    try:
        url = GEMINI_BASE.rstrip("/") + "/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
        
        prompt = (
            "Based on these travel interests: " + ", ".join(interests) + 
            " and this user input: '" + user_input + "', suggest 3-5 specific places in Sri Lanka that would be perfect for this traveler. "
            "Return ONLY a JSON list of place names (no explanations, no descriptions). "
            "Focus on popular tourist destinations that match the interests. "
            "Examples: Colombo, Kandy, Galle, Sigiriya, Ella, Nuwara Eliya, Mirissa, Yala National Park, Anuradhapura, Polonnaruwa"
        )
        
        payload = {
            "model": GEMINI_MODEL,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Suggest places for me to visit in Sri Lanka."},
            ],
            "temperature": 0.3,
        }
        
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        
        # Extract JSON array
        start = content.find("[")
        end = content.rfind("]") + 1
        if start == -1 or end <= start:
            return _fallback_place_suggestions(interests)
        
        parsed = json.loads(content[start:end])
        if isinstance(parsed, list):
            return parsed[:5]  # Limit to 5 places
        else:
            return _fallback_place_suggestions(interests)
            
    except Exception as e:
        print(f"LLM place suggestion failed: {e}")
        return _fallback_place_suggestions(interests)

def _fallback_place_suggestions(interests: List[str]) -> List[str]:
    """
    Fallback place suggestions based on interests without LLM.
    """
    place_mapping = {
        "beach": ["Mirissa", "Bentota", "Unawatuna", "Arugam Bay"],
        "culture": ["Kandy", "Anuradhapura", "Polonnaruwa", "Galle Fort"],
        "nature": ["Ella", "Nuwara Eliya", "Horton Plains", "Adam's Peak"],
        "wildlife": ["Yala National Park", "Udawalawe", "Wilpattu", "Sinharaja"],
        "adventure": ["Ella", "Adam's Peak", "Little Adam's Peak", "Nine Arch Bridge"],
        "food": ["Colombo", "Kandy", "Galle", "Negombo"],
        "wellness": ["Kandy", "Ella", "Nuwara Eliya", "Bentota"],
        "photography": ["Sigiriya", "Ella", "Galle Fort", "Mirissa"],
        "spa": ["Bentota", "Negombo", "Colombo", "Galle"]
    }
    
    suggested_places = []
    for interest in interests:
        if interest in place_mapping:
            suggested_places.extend(place_mapping[interest])
    
    # Remove duplicates and limit to 5
    unique_places = list(dict.fromkeys(suggested_places))
    return unique_places[:5] if unique_places else ["Colombo", "Kandy", "Galle"]
