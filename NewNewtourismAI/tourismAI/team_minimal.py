# team_minimal.py — Any-destination Group Planner + Route Optimizer (LLM-only, robust)
# Key fixes:
# • Unique END_TOKEN (###END###) used ONLY in agents' system messages.
# • Termination listens for END_TOKEN; user tasks never mention it.
# • Extract the last message from the assistant agent (not the user echo).
# • LLM must produce all content; no local catalogs or invented attractions.
# • If JSON parse fails: retries + raw reply shown; script exits without fabricating data.
# • If some coords missing: one LLM pass to fill ONLY lat/lon (no other edits).

import os, asyncio, math, json, re, datetime as dt
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

# ========= Config =========
END_TOKEN = "###END###"  # unique end marker to avoid premature termination

# ========= Safety + PII =========
# Very small guardrail list. In a real app you would use a richer policy.
BANNED_TOPICS = ["weapons", "explicit sexual content", "hate", "terror", "bomb", "kill"]
def policy_gate(text: str) -> tuple[bool, str]:
    lo = text.lower()
    if any(b in lo for b in BANNED_TOPICS):
        return False, "Request violates content/safety policy."
    return True, ""

# PII redaction patterns: email, phone-like strings, and credit card-like strings
PII_PATTERNS = [
    (re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b'), "<EMAIL>"),
    (re.compile(r'\b\+?\d[\d\-\s]{7,}\d\b'), "<PHONE>"),
    (re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'), "<CARD>"),
]
def redact_pii(text: str) -> str:
    s = text
    for pat, repl in PII_PATTERNS:
        s = pat.sub(repl, s)
    return s.strip()

# ========= Routing + Schedule (uses only LLM-provided coords) =========
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def greedy_route(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pts = [p for p in points if isinstance(p.get("lat"), (int,float)) and isinstance(p.get("lon"), (int,float))]
    if len(pts) < 2:
        return points[:]
    remaining = pts[:]
    cur = remaining.pop(0)
    order = [cur]
    while remaining:
        remaining.sort(key=lambda p: haversine_km(cur["lat"], cur["lon"], p["lat"], p["lon"]))
        cur = remaining.pop(0)
        order.append(cur)
    # append any missing coords at end (no invention)
    for p in points:
        if p not in order:
            order.append(p)
    return order

def estimate_drive_minutes(a, b, default=15):
    if isinstance(a.get("lat"), (int,float)) and isinstance(a.get("lon"), (int,float)) and \
       isinstance(b.get("lat"), (int,float)) and isinstance(b.get("lon"), (int,float)):
        km = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        return max(5, round((km / 22.0) * 60))  # ~22 km/h city avg
    return default

def schedule_day(route: List[Dict[str, Any]], start_time="09:00") -> List[Dict[str, Any]]:
    t = dt.datetime.combine(dt.date.today(), dt.datetime.strptime(start_time, "%H:%M").time())
    day = []
    for i, stop in enumerate(route):
        travel = 0 if i == 0 else estimate_drive_minutes(route[i-1], stop)
        if i > 0: t += dt.timedelta(minutes=travel)
        start = t
        dwell = int(stop.get("typical_minutes", 45))
        end = start + dt.timedelta(minutes=dwell)
        day.append({
            "name": stop.get("name","(unknown)"),
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
            "travel_minutes_from_prev": travel,
            "dwell_minutes": dwell,
            "tags": stop.get("tags", []),
            "cost": stop.get("cost", "n/a"),
            "reason": stop.get("reason",""),
        })
        t = end + dt.timedelta(minutes=10)  # buffer
    return day

# ========= JSON helpers =========
def find_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.I | re.S)
    candidates = []
    if m: candidates.append(m.group(1))
    m2 = re.search(r":[ \t]*({.*})", text, re.S)  # label: {...}
    if m2: candidates.append(m2.group(1))
    # generic balance
    stack = 0; start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if stack == 0: start = i
            stack += 1
        elif ch == '}':
            stack -= 1
            if stack == 0 and start is not None:
                candidates.append(text[start:i+1]); break
    for c in candidates:
        try: return json.loads(c)
        except: pass
    return None

def extract_labeled_json(label: str, text: str) -> Optional[Dict[str, Any]]:
    m = re.search(rf"{label}\s*:\s*```json\s*(\{{.*?\}})\s*```", text, re.I | re.S)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    m2 = re.search(rf"{label}\s*:\s*(\{{.*\}})", text, re.I | re.S)
    if m2:
        try: return json.loads(m2.group(1))
        except: pass
    return find_first_json_object(text)

def normalize_stops_from_llm(chosen: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm = []
    for s in chosen:
        rec = {
            "name": s.get("name","Place"),
            "typical_minutes": int(s.get("typical_minutes", 45)),
            "tags": s.get("tags", []),
            "cost": s.get("cost","n/a"),
            "mobility": s.get("mobility","easy"),
            "reason": s.get("reason",""),
        }
        lat, lon = s.get("lat"), s.get("lon")
        try:
            rec["lat"] = float(lat) if lat is not None else None
            rec["lon"] = float(lon) if lon is not None else None
        except Exception:
            rec["lat"] = None; rec["lon"] = None
        norm.append(rec)
    return norm

def have_missing_coords(stops: List[Dict[str, Any]]) -> bool:
    return any(not isinstance(s.get("lat"), (int,float)) or not isinstance(s.get("lon"), (int,float)) for s in stops)

def last_from_agent(convo, agent_name: str) -> str:
    """
    Return the content of the last message sent by the given agent.
    Falls back to the last message if fields differ by library version.
    """
    for m in reversed(convo.messages):
        src = getattr(m, "source", None) or getattr(m, "name", None) or getattr(m, "sender", None)
        if src and str(src).lower() == agent_name.lower():
            return m.content if isinstance(m.content, str) else str(m.content)
    return convo.messages[-1].content if convo.messages else ""

# ========= Main =========
async def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n[Hint] Create a .env in this folder with: GEMINI_API_KEY=YOUR_KEY\n")
        raise RuntimeError("GEMINI_API_KEY not found in .env")

    model_client = OpenAIChatCompletionClient(
        model="gemini-2.5-flash",
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_info={"function_calling": True, "vision": False, "json_output": False, "structured_output": False, "family": "gemini"},
    )

    print("\n== Group Trip Planner ==")
    print("Type INSIDE this program when prompted. If you press Enter with no text, it will exit.")
    print("If you see the PowerShell prompt (PS C:\\...>), the program has ended.\n")

    # ---- Inputs (no defaults) ----
    city = input("Destination city/town (type any place, e.g., Kandy, Galle, Ella, Paris): ").strip()
    if not city:
        print("Please enter a destination.")
        return

    raw_n = input("How many people are in the group? (e.g., 5): ").strip()
    if not raw_n.isdigit() or int(raw_n) <= 0:
        print("Please enter a positive integer.")
        return
    n = int(raw_n)

    print("\nEnter each person like: role/age + interests comma-separated.")
    print("Example: Parent 40: culture, history | Teen 15: adventure, shopping | Grandparent 70: relaxing, easy walks\n")
    members = []
    for i in range(1, n+1):
        line = input(f"Person {i}: ").strip()
        if not line:
            print("Please enter something for this person.")
            return
        members.append({"profile": redact_pii(line)})

    budget = input("\nAny budget guidance? (e.g., 'low-cost only', 'under 10,000 LKR'; leave blank if none): ").strip()
    mobility = input("Any mobility constraints? (e.g., 'avoid stairs', 'wheelchair friendly'; leave blank if none): ").strip()

    # Safety check
    ok, why = policy_gate(" ".join([city, budget, mobility] + [m['profile'] for m in members]))
    if not ok:
        print("Blocked for safety:", why)
        return

    # ----------- Agents (LLM-only generation) -----------
    example_route_request = {
        "city": "Exampleville",
        "party_summary": "Parents: culture; Teen: shopping; Elder: relaxing",
        "compromise_plan": "Culture in the morning, relaxing lunch, shopping afternoon; optional viewpoint for photos.",
        "constraints": {"budget": "low-cost", "mobility": "wheelchair friendly"},
        "chosen_stops": [
            {"name":"City Museum","lat":12.34,"lon":56.78,"typical_minutes":60,"tags":["culture","history"],"cost":"paid","mobility":"easy","reason":"indoor, accessible"},
            {"name":"Central Park","lat":12.35,"lon":56.79,"typical_minutes":45,"tags":["relaxation","nature"],"cost":"free","mobility":"easy","reason":"flat paths, benches"},
            {"name":"Market Street","lat":12.36,"lon":56.80,"typical_minutes":60,"tags":["shopping","food"],"cost":"free","mobility":"easy","reason":"affordable souvenirs"},
        ]
    }

# Planner agent: merges group needs and outputs a ROUTE_REQUEST JSON.
    group_agent = AssistantAgent(
        name="group_planner",
        description="Generates attractions for any destination, merges preferences, resolves conflicts, returns ROUTE_REQUEST JSON.",
        system_message=(
            "ROLE: Group & Social-Planning agent for tourists.\n"
            "Support ANY destination (town/city/region). Use safe public attractions. Nearby points within ~30 km allowed.\n\n"
            "TASK:\n"
            "1) Merge multi-person preferences fairly (culture/shopping/adventure/relaxation) and detect conflicts.\n"
            "2) Propose a compromise (e.g., culture morning, shopping afternoon; optional short hike for adventurous).\n"
            "3) Choose 3–5 stops for a 1-day plan.\n"
            "4) For EACH stop, you MUST provide: name, lat (decimal), lon (decimal), typical_minutes (int), tags, cost (free|low|paid), mobility (easy|stairs|trail), reason.\n"
            "   Coordinates are REQUIRED; approximate realistically if needed.\n"
            "5) OUTPUT STRICT JSON in a fenced code block with the EXACT schema below. NO extra commentary.\n\n"
            "EXAMPLE (copy structure):\n"
            "ROUTE_REQUEST:\n```json\n" + json.dumps(example_route_request, ensure_ascii=False, indent=2) + "\n```\n"
            "YOUR TURN: Use the same keys (with your content). End with " + END_TOKEN + ".\n"
        ),
        model_client=model_client,
    )
# Route optimizer agent: reorders stops and emits ROUTE_DECISION JSON.
    route_agent = AssistantAgent(
        name="route_optimizer",
        description="Orders stops efficiently and returns ROUTE_DECISION JSON.",
        system_message=( 
            "ROLE: Route-Optimization agent.\n"
            "Given a ROUTE_REQUEST, reorder stops to minimize travel (~22 km/h), respect mobility constraints, add 10-min buffers.\n"
            "OUTPUT STRICT JSON (fenced) exactly like:\n"
            "ROUTE_DECISION:\n```json\n"
            "{\n"
            '  "ordered_stops":[{"name":""}],\n'
            '  "rationale":"string",\n'
            '  "tips":"string"\n'
            "}\n"
            "```\n"
            "End with " + END_TOKEN + ". No extra text before/after the fenced JSON.\n"
        ),
        model_client=model_client,
    )

    you = UserProxyAgent(name="you")

    def group_task(strict_only=False):
        profiles = "\n".join([f"- {m['profile']}" for m in members])
        tighten = "Return ONLY the fenced JSON (no prose)." if strict_only else "Return the fenced JSON."
        return (
            f"DESTINATION: {city}\n"
            f"GROUP MEMBERS:\n{profiles}\n"
            f"BUDGET: {budget}\n"
            f"MOBILITY: {mobility}\n\n"
            "Generate attractions for this destination and follow the system instructions.\n"
            f"{tighten}"
        )

    # ---- Phase 1: Group planning with up to 3 retries --
    route_req = None
    raw_planner_replies = []
    for attempt in range(3):
        team1 = RoundRobinGroupChat(
            participants=[you, group_agent],
            termination_condition=TextMentionTermination(END_TOKEN),
            max_turns=3,
        )
        convo1 = await team1.run(task=group_task(strict_only=(attempt >= 1)))
        msg1 = last_from_agent(convo1, "group_planner")
        raw_planner_replies.append(msg1)
        route_req = extract_labeled_json("ROUTE_REQUEST", msg1)
        if route_req:
            break

    if not route_req:
        print("\n[Planner JSON parsing failed after 3 attempts]")
        print("Last raw reply from planner (for debugging):\n")
        print(raw_planner_replies[-1] if raw_planner_replies else "(no reply)")
        print("\nNo defaults will be used. Please re-run and try slightly richer interests (e.g., 'Parent 40: culture, temples; Teen 15: shopping, photos').")
        return

    # ---- Normalize EXACT LLM output (no invention) ----
    chosen = normalize_stops_from_llm(route_req.get("chosen_stops", []))

    # ---- If any coords are missing, ask a dedicated LLM pass to fill ONLY lat/lon (no other changes). ----
    if have_missing_coords(chosen):
        coord_fixer = AssistantAgent(
            name="coord_fixer",
            description="Fills lat/lon for the SAME places without changing names/order/content.",
            system_message=(
                "You will receive JSON with a 'chosen_stops' array. "
                "For any stop missing lat/lon, add realistic decimal coordinates for the destination area. "
                "DO NOT add, remove, rename, or reorder stops. Only fill lat/lon.\n"
                "Return ONLY the updated JSON in a fenced block. End with " + END_TOKEN + "."
            ),
            model_client=model_client,
        )
        you2 = UserProxyAgent(name="you2")
        team_fix = RoundRobinGroupChat(
            participants=[you2, coord_fixer],
            termination_condition=TextMentionTermination(END_TOKEN),
            max_turns=2,
        )
        fix_msg = (await team_fix.run(
            task="Here is the JSON to fix:\n```json\n" + json.dumps(
                {"city": route_req.get("city", city), "chosen_stops": chosen},
                ensure_ascii=False, indent=2
            ) + "\n```\nFill ONLY missing lat/lon. Return fenced JSON."
        )).messages[-1].content
        fixed = find_first_json_object(fix_msg)
        if fixed and isinstance(fixed.get("chosen_stops"), list):
            chosen = normalize_stops_from_llm(fixed["chosen_stops"])

    # ---- Phase 2: Route optimization (2 tries). If it fails, use greedy order based on LLM coords. ----
    decision = None
    task2 = (
        "Optimize this request:\n" + json.dumps(
            {
                "city": route_req.get("city", city),
                "constraints": route_req.get("constraints", {"budget": budget or None, "mobility": mobility or None}),
                "chosen_stops": chosen
            }, ensure_ascii=False, indent=2
        ) + "\nReturn ROUTE_DECISION JSON (fenced)."
    )
    raw_route_replies = []
    for attempt in range(2):
        team2 = RoundRobinGroupChat(
            participants=[you, route_agent],
            termination_condition=TextMentionTermination(END_TOKEN),
            max_turns=2,
        )
        convo2 = await team2.run(task=task2)
        msg2 = last_from_agent(convo2, "route_optimizer")
        raw_route_replies.append(msg2)
        decision = extract_labeled_json("ROUTE_DECISION", msg2)
        if decision:
            break

    # Order selection (no invented data)
    if decision and "ordered_stops" in decision:
        names = [o["name"] if isinstance(o, dict) else o for o in decision["ordered_stops"]]
        ordered = []
        for nm in names:
            hit = next((x for x in chosen if x["name"].lower() == nm.lower()), None)
            if hit: ordered.append(hit)
        for m in chosen:
            if all(m["name"].lower() != o["name"].lower() for o in ordered):
                ordered.append(m)
    else:
        ord_try = greedy_route(chosen)
        ordered = ord_try if ord_try else chosen

# Create a time-based itinerary beginning at 09:00 with 10-minute buffers
    day = schedule_day(ordered, start_time="09:00")

    # ---- Output to console ----
    print("\n--- Final Itinerary ---\n")
    dest = route_req.get("city", city)
    print(f"Destination: {dest}\n")
    if route_req.get("party_summary"):   print("Group:", route_req["party_summary"])
    if route_req.get("compromise_plan"): print("Compromise:", route_req["compromise_plan"])
    if budget:  print("Budget:", budget)
    if mobility:print("Mobility:", mobility)
    print()

    print(f"Total stops: {len(day)} | Travel ~{sum(x['travel_minutes_from_prev'] for x in day)} min "
          f"| On-site ~{sum(x['dwell_minutes'] for x in day)} min\n")

    for i, s in enumerate(day, start=1):
        travel = "(start)" if s["travel_minutes_from_prev"] == 0 else f"(+{s['travel_minutes_from_prev']} min travel)"
        tags = ", ".join(s["tags"]) if s["tags"] else "-"
        print(f"{i}. {s['start']}–{s['end']}  {s['name']}  {travel}")
        print(f"   • tags: {tags}  • cost: {s['cost']}  • dwell: {s['dwell_minutes']} min")
        if s["reason"]: print(f"   • why: {s['reason']}")

    print("\n###END###\n")  # purely cosmetic in console; termination already handled above

if __name__ == "__main__":
    asyncio.run(main())

