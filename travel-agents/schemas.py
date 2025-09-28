from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# ---- Parsed user request (from free text) ----
class TripQuery(BaseModel):
    raw_text: str
    destination: str
    country: Optional[str] = None
    start_date: Optional[str] = None   # ISO YYYY-MM-DD
    end_date: Optional[str] = None     # ISO YYYY-MM-DD
    nights: Optional[int] = None
    adults: int = 1
    origin_text: Optional[str] = None  # free-text origin if provided

# ---- Tool inputs ----
class FlightSearchInput(BaseModel):
    origin: str = Field(..., description="IATA origin city/airport code, e.g., LON, LHR, CMB")
    destination: str = Field(..., description="IATA destination city/airport code, e.g., PAR, CDG, TYO")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    adults: int = 1

class HotelSearchInput(BaseModel):
    city_code: str = Field(..., description="Amadeus city code, e.g., PAR, TYO")
    checkin: Optional[str] = None
    checkout: Optional[str] = None
    adults: int = 1

# ---- Flight leg detail ----
class FlightLeg(BaseModel):
    carrier: Optional[str] = None
    flight_number: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    duration_iso: Optional[str] = None
    cabin_class: Optional[str] = None

# ---- Tool outputs (normalized) ----
class FlightOption(BaseModel):
    summary: str
    price_total: float
    price_currency: str
    airline: Optional[str] = None
    deep_link: Optional[str] = None

    # Trip endpoints for friendly printing
    origin_iata: Optional[str] = None
    destination_iata: Optional[str] = None

    # Enriched round-trip info
    outbound_price: Optional[float] = None
    return_price: Optional[float] = None
    legs_outbound: List[FlightLeg] = []
    legs_return: List[FlightLeg] = []
    stops_outbound: Optional[int] = None
    stops_return: Optional[int] = None
    duration_outbound_iso: Optional[str] = None
    duration_return_iso: Optional[str] = None
    is_direct_outbound: Optional[bool] = None
    is_direct_return: Optional[bool] = None

class HotelOption(BaseModel):
    name: str
    stars: Optional[int] = None
    neighborhood: Optional[str] = None
    price_total: float
    price_currency: str
    deep_link: Optional[str] = None

class FlightSearchResult(BaseModel):
    source: Literal["duffel","amadeus","mock"] = "duffel"
    options: List[FlightOption] = []
    debug: Optional[str] = None

class HotelSearchResult(BaseModel):
    source: Literal["amadeus","mock"] = "amadeus"
    options: List[HotelOption] = []
    debug: Optional[str] = None

# ---- Combo output ----
class ComboReason(BaseModel):
    why_together: str
    pros: List[str] = []
    cons: List[str] = []

class ComboOption(BaseModel):
    title: str
    flight: FlightOption
    hotel: HotelOption
    est_total_usd: float
    currency: Literal["USD"]
    reasons: ComboReason

class FinalCombos(BaseModel):
    destination: str
    date_window: str
    combos: List[ComboOption]
