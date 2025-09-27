from pydantic import BaseModel
from typing import List, Optional, Literal

class Item(BaseModel):
    name: str
    url: Optional[str] = None
    price: Optional[float] = None
    vendor: Optional[str] = None
    reviews: Optional[List[str]] = None
    payment_methods: Optional[List[str]] = None  # e.g. ["card","cash","whatsapp"]
    city: Optional[str] = None                   # optional override for place search

class PlannerPayload(BaseModel):
    city: str
    country: Optional[str] = None
    date: Optional[str] = None
    items: List[Item]

class CheckResult(BaseModel):
    item: str
    risk: int
    signals: List[str]
    alternatives: List[str] = []

class ScamWatcherResponse(BaseModel):
    checks: List[CheckResult]

Badge = Literal["GREEN","AMBER","RED"]

class SafetyReport(BaseModel):
    badge: Badge
    reasons: List[str]
    policy_notes: List[str]
    safety_tips: List[str]
    alternatives: List[str]
    checks: List[CheckResult]
