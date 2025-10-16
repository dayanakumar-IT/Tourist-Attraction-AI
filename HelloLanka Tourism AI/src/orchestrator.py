# src/orchestrator.py
import argparse, json, sys, datetime as dt
from typing import Any, Dict
from .contracts import TripRequest, TripNormalized, ItineraryBundle
from .agents.pre_agent import normalize_themes, infer_traveler_profile
from .agents.planner_agent import PlannerAgent
from .agents.budget_weather_agent import BudgetWeatherAgent
from .settings import (
    GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE,
    OPENWEATHER_API_KEY, OPENTRIPMAP_API_KEY
)
from .tools.geocode import geocode_nominatim
from .tools.pois import diag_test_opentripmap
from .tools.weather import diag_test_openweather

def trace_print(enabled: bool, msg: str):
    if enabled: print(msg)

def run_pipeline(payload: Dict[str, Any], trace: bool=False) -> Dict[str, Any]:
    # 1) Validate incoming "frontend" payload
    req = TripRequest(**payload)

    # 2) Pre-Agent normalization
    themes = normalize_themes(req.experiences, req.free_text_interest)
    profile, src = infer_traveler_profile(req.budget.currency, req.traveler_profile_override)
    norm = TripNormalized(**req.model_dump(), themes=themes, traveler_profile=profile, inference_meta={"profile_source": src})
    trace_print(trace, f"[1/7] Pre-Agent → normalized themes: {', '.join(themes)}")
    trace_print(trace, f"[2/7] Pre-Agent → traveler_profile: {profile} ({src})")

    # 3) Planner drafts
    planner = PlannerAgent()
    trace_print(trace, "[3/7] PlannerAgent ⇢ starting route + POI selection …")
    drafts = planner.plan(norm)
    trace_print(trace, f"[4/7] PlannerAgent ⇢ drafted {len(drafts)} plan(s) with blended themes")

    # 4) Budget + Weather revision
    bw = BudgetWeatherAgent()
    trace_print(trace, "[5/7] BudgetWeatherAgent ⇢ fetching weather + computing budget …")
    finals = bw.revise(norm, drafts)
    trace_print(trace, "[6/7] BudgetWeatherAgent ⇢ revisions applied")

    # 5) Prepare response
    bundle = ItineraryBundle(plans=finals)
    trace_print(trace, f"[7/7] Finalized {len(bundle.plans)} plan(s)")
    return bundle.model_dump()

def diagnostics():
    print("=== Diagnostics: environment + live API probes ===")
    # .env presence checks
    print(f"GEMINI_API_KEY set? {'yes' if GEMINI_API_KEY else 'NO'}")
    print(f"OPENWEATHER_API_KEY set? {'yes' if OPENWEATHER_API_KEY else 'NO'}")
    print(f"OPENTRIPMAP_API_KEY set? {'yes' if OPENTRIPMAP_API_KEY else 'NO'}")

    # Geocode probe (Nominatim)
    try:
        g = geocode_nominatim("Galle, Sri Lanka")
        print(f"Nominatim OK → Galle coords: {g}")
    except Exception as e:
        print(f"Nominatim FAIL → {e}")

    # OpenTripMap probe
    try:
        diag_test_opentripmap(lat=6.0535, lon=80.2210)  # Galle center-ish
        print("OpenTripMap OK → radius query succeeded (no kinds)")
    except Exception as e:
        print(f"OpenTripMap FAIL → {e}")

    # OpenWeather probe (tomorrow)
    try:
        tomorrow = (dt.date.today() + dt.timedelta(days=1))
        diag_test_openweather(lat=6.0535, lon=80.2210, date=tomorrow)
        print("OpenWeather OK → forecast slice found")
    except Exception as e:
        print(f"OpenWeather FAIL → {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="src/input_demo.json", help="Path to JSON request")
    ap.add_argument("--trace", action="store_true", help="Print agent progress")
    ap.add_argument("--diag", action="store_true", help="Run diagnostics and exit")
    args = ap.parse_args()

    if args.diag:
        diagnostics()
        return

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"Failed to read input JSON: {e}")
        sys.exit(1)

    result = run_pipeline(payload, trace=args.trace)
    print("\n=== RESULT (3 plans max) ===")
    for i, plan in enumerate(result["plans"][:3], 1):
        print(f"\n--- PLAN {i}: {plan['title']} [{', '.join(plan['theme_mix'])}]")
        print("Budget:", plan["budget_summary"])
        for d in plan["daily_plan"]:
            print(f"  {d['date']} — {d['base_city']} (weather: {d.get('weather_hint','?')})")
            for leg in d.get("travel_legs", []):
                print(f"     travel: {leg['mode']} {leg['from']} → {leg['to']} ~ {leg.get('eta_min','?')} min ({leg.get('km','?')} km)")
            for a in d.get("activities", []):
                print(f"     activity: {a['start']} {a['name']} ({a['kind']}) ~ {a['duration_min']} min")
            for n in d.get("notes", []):
                print(f"     note: {n}")
    print("\n✅ Done.")

if __name__ == "__main__":
    main()
