from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

# ---------- INPUT from "frontend" ----------
class Party(BaseModel):
    type: Literal["solo","couple","family","friends"]
    count: int = Field(ge=1)
    notes: str = ""

class Budget(BaseModel):
    amount: float = Field(gt=0)
    currency: str  # e.g., "LKR", "USD", "CAD"

class AccommodationPref(BaseModel):
    needed: bool = False
    types: Optional[List[str]] = None  # ["hotel","resort","villa","boutique"]

class TripRequest(BaseModel):
    start_location: str
    destinations: List[str] = []
    free_text_interest: Optional[str] = None
    start_date: str  # ISO yyyy-mm-dd
    trip_days: int = Field(ge=1, le=21)
    party: Party
    budget: Budget
    accommodation: AccommodationPref
    experiences: List[str]  # raw selections e.g., ["beach","spa","adventure"]
    traveler_profile_override: Optional[Literal["local_or_expat","foreign_tourist"]] = None

# ---------- AGENT-READY INPUT (after Pre-Agent) ----------
class TripNormalized(TripRequest):
    themes: List[str]  # normalized themes
    traveler_profile: Literal["local_or_expat","foreign_tourist"]
    inference_meta: Dict[str, str] = {}

# ---------- ITINERARY STRUCTS ----------
class Activity(BaseModel):
    name: str
    kind: str                      # e.g., "beach","spa","adventure","cultural"
    start: str                     # "HH:MM"
    duration_min: int
    poi_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class TravelLeg(BaseModel):
    mode: Literal["car","train","walk","tuk"]
    from_: str = Field(alias="from")
    to: str
    eta_min: Optional[int] = None
    km: Optional[float] = None

class DayPlan(BaseModel):
    date: str
    base_city: str
    weather_hint: Optional[str] = None  # "clear"|"rainy"|"unknown"
    activities: List[Activity] = []
    travel_legs: List[TravelLeg] = []
    notes: List[str] = []

class BudgetSummary(BaseModel):
    currency: str
    per_day_estimate: Optional[int] = None
    breakdown: Dict[str, str] = {}
    affordability: Optional[Literal["Comfortable","OK","Tight"]] = None

class Itinerary(BaseModel):
    title: str
    theme_mix: List[str]
    town_order: List[str]
    daily_plan: List[DayPlan]
    budget_summary: BudgetSummary
    constraints_notes: List[str] = []

class ItineraryBundle(BaseModel):
    plans: List[Itinerary]
