# safety_policy.py
from typing import List, Literal, Optional
from schemas import PlannerPayload, ScamWatcherResponse, SafetyReport
import live_sources as live
import asyncio

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
    """
    tips: List[str] = []

    # Try 'City,CC' to make OpenWeather match the right location
    city_query = city or ""
    if country_code and len(country_code) == 2 and city:
        city_query = f"{city},{country_code.upper()}"

    wx = await live.openweather_advisory(city_query)
    if wx:
        tips.append(wx)

    if country_code:
        adv = await live.travel_advisory(country_code)
        if adv:
            score, msg = adv
            # 0..5 scale (higher = more caution). Lowered threshold so you see it in demos.
            if score >= 3.0:
                tips.append("General travel caution—prefer official providers and avoid night travel.")
            if msg:
                tips.append(("Advisory: " + msg)[:150])

    # de-dupe while preserving order
    return list(dict.fromkeys([t for t in tips if t]))[:3]

# ---------- ASYNC VERSION (use this from async code) ----------
async def merge_and_explain_async(planner: PlannerPayload, checks: ScamWatcherResponse) -> SafetyReport:
    max_risk = max((c.risk for c in checks.checks), default=0)
    badge = _badge(max_risk)

    # Human-readable reasons pulled from Scam Watcher signals
    reasons = [f"{c.item}: " + "; ".join(c.signals) for c in checks.checks if c.signals]
    if not reasons:
        reasons = ["All items passed live safety checks."]
    reasons = reasons[:6]

    # Weather + advisory
    tips = await _advisories(planner.city or "", planner.country)
    tips = tips[:3]

    # Simple policy notes based on keywords in item names
    policy_notes: List[str] = []
    names = " ".join(i.name.lower() for i in planner.items)
    if any(k in names for k in ["temple", "mosque", "stupa", "shrine"]):
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
