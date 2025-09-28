# safety_policy.py
from typing import List, Literal, Optional, Union
from schemas import PlannerPayload, ScamWatcherResponse, SafetyReport
import live_sources as live
import asyncio
import os

# Read env flag (optional): if set to 1, we will always add at least one tip
ALWAYS_TIP = os.getenv("ALWAYS_TIP", "0") == "1"

def _to_int_risk(risk: Union[int, str]) -> int:
    """Accept 40 or '40%' and return 40; default to 0 on unexpected values."""
    if isinstance(risk, int):
        return risk
    if isinstance(risk, str):
        s = risk.strip()
        if s.endswith("%"):
            s = s[:-1].strip()
        try:
            return int(float(s))
        except Exception:
            return 0
    return 0

def _badge(max_risk: int) -> Literal["GREEN", "AMBER", "RED"]:
    if max_risk < 30:
        return "GREEN"
    if max_risk < 60:
        return "AMBER"
    return "RED"

async def _advisories(city: str, country_code: Optional[str]) -> List[str]:
    """
    Build short, actionable tips from live sources.
    - Weather tip via OpenWeather (uses 'City,CC' if CC looks like ISO2).
    - Country advisory via travel-advisory.info.
    Always returns at least one tip (fallback) if nothing triggered.
    """
    tips: List[str] = []

    # Try 'City,CC' to make OpenWeather match the right location
    city_query = city or ""
    if country_code and len(country_code) == 2 and city:
        city_query = f"{city},{country_code.upper()}"

    # Weather
    wx = await live.openweather_advisory(city_query)
    if wx:
        tips.append(wx)

    # Travel advisory
    if country_code:
        adv = await live.travel_advisory(country_code)
        if adv:
            score, msg = adv
            # 0..5 scale (higher = more caution). Threshold tuned for demos.
            if score >= 3.0:
                tips.append("General travel caution—prefer official providers and avoid night travel.")
            if msg:
                tips.append(("Advisory: " + msg)[:150])

    # De-duplicate and trim
    tips = list(dict.fromkeys([t for t in tips if t]))[:3]

    # Ensure at least one useful tip:
    # - If nothing triggered, or ALWAYS_TIP=1, add a generic fallback
    if (not tips) or ALWAYS_TIP:
        generic = live.fallback_generic_tip()
        # put generic at the end if we already have tips
        if generic and (not tips or tips[-1] != generic):
            tips = (tips + [generic])[:3]

    return tips

# ---------- ASYNC VERSION (use this from async code) ----------
async def merge_and_explain_async(planner: PlannerPayload, checks: ScamWatcherResponse) -> SafetyReport:
    # Accept risk as int or 'NN%' and compute badge robustly
    max_risk = 0
    for c in checks.checks:
        max_risk = max(max_risk, _to_int_risk(c.risk))
    badge = _badge(max_risk)

    # Human-readable reasons pulled from Scam Watcher signals
    reasons = [f"{c.item} (Risk: {c.risk}%) → " + "; ".join(c.signals) for c in checks.checks if c.signals]
    if not reasons:
        reasons = ["All items passed live safety checks."]
    reasons = reasons[:6]

    # Weather + advisory (now guaranteed to return at least one tip)
    tips = await _advisories(planner.city or "", planner.country)
    tips = tips[:3]

    # Simple policy notes based on keywords in item names
    policy_notes: List[str] = []
    names = " ".join(i.name.lower() for i in planner.items)
    if any(k in names for k in ["temple", "mosque", "stupa", "shrine", "kovil"]):
        policy_notes.append("Religious sites: dress code applies (cover shoulders/knees).")
    if any(k in names for k in ["drone", "heritage", "park"]):
        policy_notes.append("Permits may be required for drones & heritage zones.")
    if not policy_notes:
        policy_notes.append("Verify vendor identity; prefer card payments with receipts.")
    policy_notes = list(dict.fromkeys(policy_notes))[:3]

    # Aggregate safer alternatives from item checks or use a default
    alternatives: List[str] = []
    for c in checks.checks:
        alternatives.extend(c.alternatives or [])
    if not alternatives:
        alternatives = ["Use official websites or buy at venue counters."]
    alternatives = list(dict.fromkeys(alternatives))[:3]

    return SafetyReport(
        badge=badge,
        reasons=reasons,
        policy_notes=policy_notes,
        safety_tips=tips,
        alternatives=alternatives,
        checks=checks.checks,
    )

# ---------- SYNC WRAPPER (safe to call only when no loop is running) ----------
def merge_and_explain(planner: PlannerPayload, checks: ScamWatcherResponse) -> SafetyReport:
    """Call this from synchronous scripts only.
    If you're already inside 'async def', use:
        await merge_and_explain_async(planner, checks)
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop → it's safe to create one.
        return asyncio.run(merge_and_explain_async(planner, checks))
    else:
        raise RuntimeError(
            "merge_and_explain() called inside a running event loop. "
            "Use 'await merge_and_explain_async(...)' instead."
        )
