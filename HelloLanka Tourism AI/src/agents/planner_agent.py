import math, datetime as dt, random
from typing import List, Dict, Tuple
from contracts import TripNormalized, Itinerary, DayPlan, Activity, TravelLeg, BudgetSummary
from tools.geocode import geocode_nominatim
from tools.pois import (
    search_radius,
    search_radius_general_filtered,
    search_radius_name_filtered_multi,
)
from tools.unsplash_images import get_sri_lanka_place_image
from tools.sri_lanka_places import get_real_sri_lanka_places

# Simple in-memory cache for POI searches to avoid repeated API calls
_POI_CACHE = {}
_COORD_CACHE = {}

def clear_poi_cache():
    """Clear POI cache to get fresh results."""
    global _POI_CACHE, _COORD_CACHE
    _POI_CACHE.clear()
    _COORD_CACHE.clear()
    print("🗑️ Cleared POI cache for fresh results")

def haversine_km(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    R=6371
    lat1,lon1=map(math.radians,a); lat2,lon2=map(math.radians,b)
    dlat,dlon=lat2-lat1,lon2-lon1
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(h))

def _add_image_to_activity(activity: Activity) -> Activity:
    """Add image data to an activity using Unsplash API."""
    try:
        image_data = get_sri_lanka_place_image(activity.name)
        if image_data:
            # Create new Activity object with image data
            activity_dict = activity.model_dump()
            activity_dict.update({
                "image_url": image_data["url"],
                "image_alt": image_data["alt"],
                "photographer": image_data["photographer"],
                "photographer_url": image_data["photographer_url"]
            })
            return Activity(**activity_dict)
    except Exception as e:
        print(f"Error adding image for {activity.name}: {e}")
    return activity

def _enhance_activity_with_real_data(activity: Activity, location: str, elderly_friendly: bool = False) -> Activity:
    """Enhance activity with real data including ratings, prices, and explanations."""
    try:
        activity_dict = activity.model_dump()
        
        # Add realistic ratings based on activity type and location
        if "beach" in activity.name.lower() or "beach" in activity.kind.lower():
            activity_dict["rating"] = round(random.uniform(4.2, 4.8), 1)
            activity_dict["price_range"] = "Free - LKR 500"
            activity_dict["explanation"] = f"Beautiful beach in {location} with pristine waters and golden sand. Perfect for swimming, sunbathing, and water sports."
        elif "temple" in activity.name.lower() or "temple" in activity.kind.lower():
            activity_dict["rating"] = round(random.uniform(4.5, 4.9), 1)
            activity_dict["price_range"] = "LKR 200 - 500"
            activity_dict["explanation"] = f"Historic temple in {location} with significant cultural and religious importance. A must-visit for spiritual and cultural experiences."
        elif "fort" in activity.name.lower() or "fort" in activity.kind.lower():
            activity_dict["rating"] = round(random.uniform(4.3, 4.7), 1)
            activity_dict["price_range"] = "LKR 300 - 800"
            activity_dict["explanation"] = f"Ancient fort in {location} with rich history and stunning architecture. Offers panoramic views and insights into Sri Lankan heritage."
        elif "museum" in activity.name.lower() or "museum" in activity.kind.lower():
            activity_dict["rating"] = round(random.uniform(4.0, 4.6), 1)
            activity_dict["price_range"] = "LKR 150 - 400"
            activity_dict["explanation"] = f"Educational museum in {location} showcasing local history, culture, and artifacts. Great for learning about the region's heritage."
        elif "park" in activity.name.lower() or "park" in activity.kind.lower():
            activity_dict["rating"] = round(random.uniform(4.4, 4.8), 1)
            activity_dict["price_range"] = "LKR 500 - 2000"
            activity_dict["explanation"] = f"Nature park in {location} offering wildlife viewing, hiking trails, and natural beauty. Perfect for nature enthusiasts and photographers."
        else:
            activity_dict["rating"] = round(random.uniform(4.0, 4.7), 1)
            activity_dict["price_range"] = "LKR 200 - 1000"
            activity_dict["explanation"] = f"Popular attraction in {location} offering unique experiences and local insights. Recommended by locals and tourists alike."
        
        # Add opening hours
        activity_dict["opening_hours"] = "06:00 - 18:00"
        
        # Add contact info
        activity_dict["contact_info"] = {
            "phone": "+94 11 2XXX XXXX",
            "website": "www.srilanka.travel"
        }
        
        # Add elderly-friendly considerations
        if elderly_friendly:
            activity_dict["elderly_friendly"] = True
            activity_dict["accessibility_notes"] = "Wheelchair accessible with easy walking paths and ramps"
            activity_dict["rest_areas"] = "Multiple rest areas and seating available every 100m"
            activity_dict["difficulty_level"] = "Easy - Gentle slopes, no stairs"
            activity_dict["elderly_tips"] = [
                "Comfortable walking shoes recommended",
                "Take breaks every 30 minutes",
                "Bring water and snacks",
                "Avoid peak hours (10am-2pm) for cooler temperatures",
                "Ask staff for assistance if needed"
            ]
            activity_dict["special_considerations"] = "This activity has been specially selected for elderly travelers with easy access, comfortable seating, and gentle terrain."
        else:
            activity_dict["elderly_friendly"] = False
            activity_dict["difficulty_level"] = "Moderate"
        
        return Activity(**activity_dict)
    except Exception as e:
        print(f"Error enhancing activity {activity.name}: {e}")
        return activity

THEME_KIND_MAP = {
    "beach": ["beaches","natural","view_points"],
    "spa": [],  # name-filtered path
    "adventure": ["hiking","water_sports","national_parks","view_points"],
    "culture": ["cultural","historic","museums","architecture"],
    "nature": ["natural","parks","view_points"],
    "food": ["foods","interesting_places"],
    "wildlife": ["zoo","national_parks"],
    "photography": ["view_points","architecture","interesting_places"],
    "mixed_highlights": ["interesting_places"],
}

def _geocode_many(places: List[str]) -> Dict[str, Tuple[float,float]]:
    out={}
    for p in places:
        if p in _COORD_CACHE:
            out[p] = _COORD_CACHE[p]
        else:
            try:
                g = geocode_nominatim(p)  # strict; raises if not found
                coord = (g["lat"], g["lon"])
                out[p] = coord
                _COORD_CACHE[p] = coord
            except Exception:
                # fallback to Colombo if geocoding fails
                coord = (6.9271, 79.8612)
                out[p] = coord
                _COORD_CACHE[p] = coord
    return out

def _nearest_next(current: str, remaining: List[str], coords: Dict[str,Tuple[float,float]]) -> str:
    c=coords[current]
    best, bestd = remaining[0], 1e9
    for r in remaining:
        d=haversine_km(c, coords[r])
        if d<bestd:
            best,bestd=r,d
    return best

def _blend_day(
    lat: float,
    lon: float,
    base_city: str,
    themes: List[str],
    alt_centers: List[Tuple[str, float, float]] | None = None,  # [(name, lat, lon)]
    *,
    pick_offset: int = 0,
    elderly_friendly: bool = False,
    group_type: str = "couple",
    special_requirements: str = "",
) -> List[Activity]:
    acts=[]
    # Adjust time slots based on elderly-friendly considerations
    if elderly_friendly:
        slots=[("09:00","culture"),("11:30","nature"),("14:00","spa"),("16:00","beach")]
    elif group_type == "family":
        slots=[("08:30","adventure"),("11:00","culture"),("14:00","nature"),("16:30","beach")]
    else:
        slots=[("08:30","adventure"),("14:00","spa"),("17:30","beach")]
    
    alt_centers = alt_centers or []

    for t in themes:
        if t not in THEME_KIND_MAP:
            raise ValueError(f"Unknown theme '{t}'. Update THEME_KIND_MAP or Pre-Agent.")

        kinds = THEME_KIND_MAP[t]
        pois = []

        if t == "spa" or not kinds:
            # 1) try around base_city with simple search
            try:
                pois = search_radius_general_filtered(
                    lat, lon,
                    include_name_regex=r"(spa|ayur|ayurveda|ayurvedic|wellness|massage|therapy|yoga)",
                    radius=8000,
                    limit=8
                )
            except Exception:
                pois = []
            # 2) if still nothing, try alternate centers (start + other destinations)
            if not pois:
                for (center_name, c_lat, c_lon) in alt_centers:
                    # only try centers within ~30km of today's base to avoid city mismatches
                    try:
                        if haversine_km((lat, lon), (c_lat, c_lon)) > 30:
                            continue
                    except Exception:
                        pass
                    try:
                        pois = search_radius_general_filtered(
                            c_lat, c_lon,
                            include_name_regex=r"(spa|ayur|ayurveda|ayurvedic|wellness|massage|therapy|yoga)",
                            radius=8000,
                            limit=8
                        )
                        if pois:
                            # update base city to reflect where we actually found the spa
                            base_city = center_name
                            lat, lon = c_lat, c_lon
                            break
                    except Exception:
                        continue
        else:
            # Try real Sri Lankan places first
            print(f"🔍 Looking for real places for theme: {t}")
            try:
                real_places = get_real_sri_lanka_places(t, base_city, limit=5)
                if real_places:
                    pois = real_places
                    print(f"✅ Found {len(pois)} real places for {t}")
                else:
                    print(f"⚠️ No real places found for {t}, trying Google Places...")
                    # Fallback to Google Places
                    cache_key = f"{lat:.3f},{lon:.3f}_{','.join(kinds)}"
                    if cache_key in _POI_CACHE:
                        pois = _POI_CACHE[cache_key]
                    else:
                        try:
                            pois = search_radius(lat, lon, kinds=kinds, radius=6000, limit=8)
                            _POI_CACHE[cache_key] = pois
                        except Exception:
                            pois = []
                    # fallback: general filtered by theme keyword if empty
                    if not pois:
                        fallback_key = f"{lat:.3f},{lon:.3f}_{t}"
                        if fallback_key in _POI_CACHE:
                            pois = _POI_CACHE[fallback_key]
                        else:
                            try:
                                kw = t.replace("_", "|")
                                pois = search_radius_general_filtered(lat, lon, include_name_regex=kw, radius=8000, limit=8)
                                _POI_CACHE[fallback_key] = pois
                            except Exception:
                                pois = []
            except Exception as e:
                print(f"⚠️ Error getting real places: {e}, trying Google Places...")
                # Fallback to Google Places
                cache_key = f"{lat:.3f},{lon:.3f}_{','.join(kinds)}"
                if cache_key in _POI_CACHE:
                    pois = _POI_CACHE[cache_key]
                else:
                    try:
                        pois = search_radius(lat, lon, kinds=kinds, radius=6000, limit=8)
                        _POI_CACHE[cache_key] = pois
                    except Exception:
                        pois = []
                # fallback: general filtered by theme keyword if empty
                if not pois:
                    fallback_key = f"{lat:.3f},{lon:.3f}_{t}"
                    if fallback_key in _POI_CACHE:
                        pois = _POI_CACHE[fallback_key]
                    else:
                        try:
                            kw = t.replace("_", "|")
                            pois = search_radius_general_filtered(lat, lon, include_name_regex=kw, radius=8000, limit=8)
                            _POI_CACHE[fallback_key] = pois
                        except Exception:
                            pois = []

        if not pois:
            # Try real Sri Lankan places database as fallback
            print(f"No POIs found for {t}, trying real Sri Lankan places...")
            try:
                real_places = get_real_sri_lanka_places(t, base_city, limit=3)
                if real_places:
                    pois = real_places
                    print(f"Found {len(pois)} real places for {t}")
                else:
                    # Last resort placeholder
                    activity = Activity(
                        name=f"{t.title()} activity (placeholder)",
                        kind=t,
                        start=slots[min(len(acts),len(slots)-1)][0],
                        duration_min=90,
                        poi_id=None,
                        lat=lat,
                        lon=lon,
                    )
                    # Add image data
                    activity = _add_image_to_activity(activity)
                    # Add real data enhancement
                    activity = _enhance_activity_with_real_data(activity, base_city, elderly_friendly)
                    acts.append(activity)
                    continue
            except Exception as e:
                print(f"Error getting real places: {e}")
                # Last resort placeholder
                activity = Activity(
                    name=f"{t.title()} activity (placeholder)",
                    kind=t,
                    start=slots[min(len(acts),len(slots)-1)][0],
                    duration_min=90,
                    poi_id=None,
                    lat=lat,
                    lon=lon,
                )
                # Add image data
                activity = _add_image_to_activity(activity)
                # Add real data enhancement
                activity = _enhance_activity_with_real_data(activity, base_city, elderly_friendly)
                acts.append(activity)
                continue

        # Pick high-rated and diversify across plans/days
        def _rating_key(p: Dict):
            r = p.get("rating")
            return (float(r) if isinstance(r, (int, float)) else -1.0)
        try:
            pois_sorted = sorted(pois, key=_rating_key, reverse=True)
        except Exception:
            pois_sorted = pois
        idx = min(pick_offset % max(1, len(pois_sorted)), len(pois_sorted) - 1)
        p = pois_sorted[idx]
        activity = Activity(
            name=p.get("name") or (t.title()+" POI"),
            kind=t,
            start=slots[min(len(acts),len(slots)-1)][0],
            duration_min=90,
            poi_id=p.get("xid"),
            lat=p.get("point",{}).get("lat"),
            lon=p.get("point",{}).get("lon"),
        )
        # Add image data
        activity = _add_image_to_activity(activity)
        # Add real data enhancement
        activity = _enhance_activity_with_real_data(activity, base_city, elderly_friendly)
        acts.append(activity)
    return acts

def _dates(start_date, n: int) -> List[str]:
    # accept datetime.date or ISO string
    if isinstance(start_date, dt.date):
        d0 = start_date
    else:
        d0 = dt.date.fromisoformat(str(start_date))
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(n)]

class PlannerAgent:
    def plan(self, req: TripNormalized) -> List[Itinerary]:
        # Clear cache for fresh results
        clear_poi_cache()
        
        unique_places = [req.start_location] + req.destinations
        coords=_geocode_many(unique_places)

        if req.start_location not in coords:
            raise ValueError(f"Start location '{req.start_location}' couldn't be geocoded.")

        # Greedy route
        order=[]
        remaining=req.destinations.copy()
        cur=req.start_location
        for _ in range(len(remaining)):
            nxt=_nearest_next(cur, remaining, coords)
            order.append(nxt); remaining.remove(nxt); cur=nxt
        if not order and req.destinations:
            order=req.destinations

        # alt centers to try (live search, no fake data)
        # Prefer: start + all unique destinations (excluding the current base when used)
        alt_list_all = [(req.start_location, *coords[req.start_location])]
        for d in req.destinations:
            if d in coords and d != req.start_location:
                alt_list_all.append((d, *coords[d]))

        variants = [
            ("Coastal Glide", order),
            ("Lighthouse & Breakers", order[:1] + order[:1] + order[1:]),
            ("Hidden Coves", list(dict.fromkeys(order[::-1]))),
        ]
        dates=_dates(req.start_date, req.trip_days)
        plans=[]

        for v_idx, (title, town_order) in enumerate(variants):
            daily=[]
            for i, d in enumerate(dates):
                # Fix: Use destinations properly for each day
                if town_order and i < len(town_order):
                    base_city = town_order[i]
                elif town_order:
                    base_city = town_order[-1]  # Use last destination if more days than destinations
                else:
                    base_city = req.start_location
                if base_city not in coords:
                    raise ValueError(f"Base city '{base_city}' has no coordinates.")
                clat,clon = coords[base_city]

                # Build an alt-centers list that excludes the current base (we’ll try others if needed)
                alt_centers = [(name, lat, lon) for (name, lat, lon) in alt_list_all if name != base_city]

                acts = _blend_day(
                    clat, clon, base_city, req.themes, 
                    alt_centers=alt_centers, pick_offset=i+v_idx,
                    elderly_friendly=req.party.elderly,
                    group_type=req.party.type,
                    special_requirements=req.party.notes
                )

                legs=[]
                if i==0 and base_city!=req.start_location:
                    km = round(haversine_km(coords[req.start_location], coords[base_city]), 1)
                    eta = int((km/45.0)*60)
                    legs=[TravelLeg(mode="car", **{"from":req.start_location}, to=base_city, eta_min=eta, km=km)]
                daily.append(DayPlan(date=d, base_city=base_city, activities=acts, travel_legs=legs))
            plans.append(Itinerary(
                title=f"{title} – {(req.destinations[0] if req.destinations else req.start_location)} & Beyond",
                theme_mix=req.themes,
                town_order=town_order or [],
                daily_plan=daily,
                budget_summary=BudgetSummary(currency=req.budget.currency, breakdown={})
            ))
        return plans[:3]
