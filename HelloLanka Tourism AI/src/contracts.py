# src/tools/contracts.py (revised)
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, constr, conint, conlist

# ---------- INPUT from "frontend" ----------

class Party(BaseModel):
    type: Literal["solo", "couple", "family", "friends"]
    count: conint(ge=1) = 1
    notes: str = ""

    class Config:
        extra = "forbid"


CurrencyCode = constr(regex=r"^[A-Z]{3}$")  # e.g., USD, LKR, EUR

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
WeatherHint = Literal["clear", "rainy", "unknown"]

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

    class Config:
        extra = "forbid"


class TravelLeg(BaseModel):
    mode: Literal["car", "train", "walk", "tuk"]  # add "bus" if you plan to support it
    from_: str = Field(alias="from")
    to: str
    eta_min: Optional[conint(ge=0)] = None
    km: Optional[float] = None

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"


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
    plans: conlist(Itinerary, min_items=1)

    class Config:
        extra = "forbid"
