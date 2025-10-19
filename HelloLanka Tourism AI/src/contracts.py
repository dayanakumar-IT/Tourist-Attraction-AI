# src/tools/contracts.py (revised)
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, constr, conint, conlist
from pydantic.config import ConfigDict

# ---------- INPUT from "frontend" ----------

class Party(BaseModel):
    type: Literal["solo", "couple", "family", "friends"]
    count: conint(ge=1) = 1
    notes: str = ""

    class Config:
        extra = "forbid"


CurrencyCode = constr(pattern=r"^[A-Z]{3}$")  # e.g., USD, LKR, EUR

class Budget(BaseModel):
    amount: Decimal = Field(gt=0)   # use Decimal for money; ok to switch back to float if you prefer
    currency: CurrencyCode          # e.g., "LKR", "USD", "CAD"

    class Config:
        extra = "forbid"


class AccommodationPref(BaseModel):
    needed: bool = False
    types: Optional[List[str]] = None  # ["hotel","resort","villa","boutique"]

    class Config:
        extra = "forbid"


class TripRequest(BaseModel):
    start_location: str
    destinations: List[str] = Field(default_factory=list)
    free_text_interest: Optional[str] = None
    start_date: date                     # ISO yyyy-mm-dd accepted; pydantic parses str -> date
    trip_days: conint(ge=1, le=21) = 1
    party: Party
    budget: Budget
    accommodation: AccommodationPref
    experiences: List[str] = Field(default_factory=list)  # e.g., ["beach","spa","adventure"]
    traveler_profile_override: Optional[Literal["local_or_expat", "foreign_tourist"]] = None

    class Config:
        extra = "forbid"


# ---------- AGENT-READY INPUT (after Pre-Agent) ----------

class TripNormalized(TripRequest):
    themes: List[str] = Field(default_factory=list)  # normalized themes (kinds)
    traveler_profile: Literal["local_or_expat", "foreign_tourist"]
    inference_meta: Dict[str, str] = Field(default_factory=dict)

    class Config:
        extra = "forbid"


# ---------- ITINERARY STRUCTS ----------

# If you prefer a stricter enum:
WeatherHint = Literal["clear", "rainy", "unknown", "partly_cloudy", "sunny", "cloudy", "light_rain"]

class Activity(BaseModel):
    name: str
    kind: str                         # e.g., "beach","spa","adventure","cultural"
    start: time                       # "HH:MM" accepted; pydantic parses
    duration_min: conint(ge=0) = 0

    # Geo/POI metadata (Google Places–friendly)
    poi_id: Optional[str] = None      # Google place_id
    lat: Optional[float] = None
    lon: Optional[float] = None
    types: Optional[List[str]] = None # Google 'types' list
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None

    # Enhanced data from WeatherFoodAgent
    weather_info: Optional[Dict[str, Any]] = None
    nearby_restaurants: Optional[List[Dict[str, Any]]] = None
    timing_info: Optional[Dict[str, Any]] = None
    
    # Image data from Unsplash
    image_url: Optional[str] = None
    image_alt: Optional[str] = None
    photographer: Optional[str] = None
    photographer_url: Optional[str] = None
    
    # Cultural and safety tips
    cultural_tips: Optional[Dict[str, Any]] = None
    safety_tips: Optional[List[str]] = None
    local_etiquette: Optional[List[str]] = None
    special_notes: Optional[str] = None
    
    # Real data integration
    price_range: Optional[str] = None
    opening_hours: Optional[str] = None
    contact_info: Optional[Dict[str, str]] = None
    explanation: Optional[str] = None  # Explainable AI

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class TravelLeg(BaseModel):
    mode: Literal["car", "train", "walk", "tuk", "bus"]  # Added bus option
    from_: str = Field(alias="from")
    to: str
    eta_min: Optional[conint(ge=0)] = None
    km: Optional[float] = None
    estimated_cost: Optional[int] = None
    cost_currency: Optional[str] = None
    
    # Train-specific fields
    scenic_rating: Optional[int] = None
    booking_url: Optional[str] = None
    available_classes: Optional[List[str]] = None
    frequency: Optional[str] = None
    recommendations: Optional[List[str]] = None
    
    # Explainable AI
    explanation: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DayPlan(BaseModel):
    date: date
    base_city: str
    weather_hint: Optional[WeatherHint] = None
    activities: List[Activity] = Field(default_factory=list)
    travel_legs: List[TravelLeg] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class BudgetSummary(BaseModel):
    currency: CurrencyCode
    per_day_estimate: Optional[int] = None
    breakdown: Dict[str, str] = Field(default_factory=dict)
    affordability: Optional[Literal["Comfortable", "OK", "Tight"]] = None

    class Config:
        extra = "forbid"


class Itinerary(BaseModel):
    title: str
    theme_mix: List[str] = Field(default_factory=list)
    town_order: List[str] = Field(default_factory=list)
    daily_plan: List[DayPlan] = Field(default_factory=list)
    budget_summary: BudgetSummary
    constraints_notes: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class ItineraryBundle(BaseModel):
    plans: conlist(Itinerary, min_length=1)

    class Config:
        extra = "forbid"
