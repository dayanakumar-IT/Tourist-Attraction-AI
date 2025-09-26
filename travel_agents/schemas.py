from __future__ import annotations
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

#Pydantic models are used to define data structures with validation
# TripQuery is a pydantic model
class TripQuery(BaseModel):
    origin: Optional[str] = Field(None, description="Origin city or IATA code")
    destination: str = Field(..., description="Destination city, country or IATA code")  
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    nights: Optional[int] = Field(None, ge=1, description="Length of stay if dates omitted")
    adults: int = Field(1, ge=1)
    budget_lkr: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None 

class FlightOption(BaseModel):
    provider: str
    summary: str
    price_currency: str
    price_total: float
    deep_link: Optional[HttpUrl] = None

class HotelOption(BaseModel):
    provider: str
    name: str
    city: str
    price_currency: str
    price_total: float
    check_in: str
    check_out: str
    address: Optional[str] = None
    deep_link: Optional[HttpUrl] = None

class PackageOption(BaseModel):
    title: str
    flights: FlightOption
    hotel: HotelOption
    est_total_currency: str
    est_total: float


class PlanResponse(BaseModel):
    query: TripQuery
    packages: List[PackageOption]
    missing: List[str] = []

class PlannerPayload(BaseModel):
    query: TripQuery
    plan: PlanResponse