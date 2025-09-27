# api.py
import os
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from team_minimal import run_agents  # <-- imports your async function

# FastAPI app
app = FastAPI(title="Tourism AI", version="1.0")

# CORS for local dev (React at http://localhost:5173 by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PlanRequest(BaseModel):
    city: str = Field(..., examples=["Kandy"])
    total_budget_lkr: int = Field(..., examples=[5000])
    travelers: int = 2
    include_free_alternatives: int = 2

class ChatRequest(BaseModel):
    # free-text “chat” – we’ll parse a few simple hints
    message: str

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/plan")
async def plan(req: PlanRequest):
    # directly call your pipeline
    out = await run_agents(
        city=req.city,
        total_budget_lkr=req.total_budget_lkr,
        travelers=req.travelers,
        include_free_alternatives=req.include_free_alternatives,
    )
    return out

# Optional: a very light “chat” endpoint that guesses city/budget from text
import re
def _guess_city_and_budget(msg: str):
    # naive parse; improve later
    city = None
    budget = None
    # city ~ the first capitalized word after "to" or "in"
    m = re.search(r"\b(?:to|in)\s+([A-Z][a-zA-Z]+)", msg)
    if m: city = m.group(1)
    # number + “lkr|rs|rupees”
    m = re.search(r"(\d{3,6})\s*(?:lkr|rs|rupees)", msg, re.I)
    if m: budget = int(m.group(1))
    return city or "Kandy", budget or 5000

@app.post("/chat")
async def chat(req: ChatRequest):
    city, budget = _guess_city_and_budget(req.message)
    out = await run_agents(city=city, total_budget_lkr=budget, travelers=2, include_free_alternatives=2)
    # make the response look chatty while still returning data
    return {
        "role": "assistant",
        "city": city,
        "budget_lkr": budget,
        "data": out["data"] if out.get("ok") else None,
        "raw": out.get("raw_output")
    }
