# team_minimal.py — Attraction Finder + Rating Analyzer (LLM-only, robust, emoji UI)
# Inputs: city, interests, number of free/low-cost alternatives
# Output: actual places (from Gemini) with name, category, best time/season, notes, rating

import os, asyncio, json, re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

# ========= Config =========
END_TOKEN = "###END###"

# ========= Safety + PII =========
BANNED_TOPICS = ["weapons", "explicit sexual content", "hate", "terror", "bomb", "kill"]

def policy_gate(text: str) -> tuple[bool, str]:
    lo = text.lower()
    if any(b in lo for b in BANNED_TOPICS):
        return False, "Request violates content/safety policy."
    return True, ""

import re as _re
PII_PATTERNS = [
    (_re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b'), "<EMAIL>"),
    (_re.compile(r'\b\+?\d[\d\-\s]{7,}\d\b'), "<PHONE>"),
    (_re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'), "<CARD>"),
]
def redact_pii(text: str) -> str:
    s = text
    for pat, repl in PII_PATTERNS:
        s = pat.sub(repl, s)
    return s.strip()

# ========= JSON helpers =========
def find_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"json\s*(\{.*?\})\s*", text, re.I | re.S)
    candidates = []
    if m:
        candidates.append(m.group(1))
    m2 = re.search(r":[ \t]({.})", text, re.S)
    if m2:
        candidates.append(m2.group(1))
    stack = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if stack == 0:
                start = i
            stack += 1
        elif ch == '}':
            stack -= 1
            if stack == 0 and start is not None:
                candidates.append(text[start:i+1])
                break
    for c in candidates:
        try:
            return json.loads(c)
        except Exception:
            pass
    return None

def extract_labeled_json(label: str, text: str) -> Optional[Dict[str, Any]]:
    m = re.search(rf"{label}\s*:\s*json\s*(\{{.*?\}})\s*", text, re.I | re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m2 = re.search(rf"{label}\s*:\s*(\{{.*\}})", text, re.I | re.S)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            pass
    return find_first_json_object(text)

def last_from_agent(convo, agent_name: str) -> str:
    for m in reversed(convo.messages):
        src = getattr(m, "source", None) or getattr(m, "name", None) or getattr(m, "sender", None)
        if src and str(src).lower() == agent_name.lower():
            return m.content if isinstance(m.content, str) else str(m.content)
    return convo.messages[-1].content if convo.messages else ""

def normalize_attractions(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm = []
    for x in items or []:
        norm.append({
            "name": (x.get("name") or "").strip() or "Unknown",
            "category": (x.get("category") or "").strip() or "-",
            "best_time": (x.get("best_time") or x.get("season") or "").strip() or "-",
            "notes": (x.get("notes") or x.get("why") or "").strip() or "",
            "rating": float(x.get("rating", 0.0)) if str(x.get("rating", "")).strip() != "" else 0.0,
            "cost": (x.get("cost") or "").strip().lower() or "unspecified",
        })
    seen = set(); out = []
    for it in norm:
        key = it["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

# ========= Emoji helpers =========
def cost_emoji(cost: str) -> str:
    c = (cost or "").lower()
    if "free" in c:
        return "🆓"
    if "low" in c or "cheap" in c or "budget" in c:
        return "💸"
    if "paid" in c or "ticket" in c or "fee" in c:
        return "💵"
    return "💠"

def category_emoji(cat: str) -> str:
    c = (cat or "").lower()
    if "museum" in c: return "🏛️"
    if "temple" in c or "shrine" in c: return "🛕"
    if "church" in c or "cathedral" in c: return "⛪"
    if "park" in c or "garden" in c: return "🌿"
    if "market" in c or "bazaar" in c: return "🛍️"
    if "view" in c or "tower" in c or "sky" in c: return "🌄"
    if "beach" in c: return "🏖️"
    if "palace" in c or "fort" in c: return "🏰"
    if "neighborhood" in c or "street" in c: return "🏘️"
    return "📍"

def time_emoji(bt: str) -> str:
    s = (bt or "").lower()
    # months/seasons/dayparts
    if any(m in s for m in ["nov", "dec", "jan", "feb", "winter"]): return "❄️"
    if any(m in s for m in ["mar", "apr", "may", "spring"]): return "🌸"
    if any(m in s for m in ["jun", "jul", "aug", "summer"]): return "☀️"
    if any(m in s for m in ["sep", "oct", "autumn", "fall"]): return "🍂"
    if "sunrise" in s or "morning" in s: return "🌅"
    if "afternoon" in s: return "🌤️"
    if "sunset" in s or "evening" in s: return "🌇"
    if "night" in s: return "🌙"
    return "🕒"

def stars(r: float) -> str:
    # 5-star bar with half step approximation
    r = max(0.0, min(5.0, float(r or 0.0)))
    full = int(r)
    half = 1 if (r - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★"*full + ("½" if half else "") + "☆"*empty

# ========= Pretty printing =========
def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No attractions found.\n")
        return

    # header
    print("🏙️  Top Attractions\n")
    headers = ["#", "Place", "Category", "Best time", "Rating", "Cost"]
    widths  = [3, 36, 18, 18, 11, 6]

    def trunc(s, w):
        s = (s or "").replace("\n", " ").strip()
        return s if len(s) <= w else (s[:w-1] + "…")

    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    print(fmt.format(*headers))
    print("-" * (sum(widths) + (len(widths)-1)*2))

    for i, r in enumerate(rows, 1):
        name = f"{category_emoji(r['category'])} {trunc(r['name'], widths[1]-2)}"
        cat  = trunc(r["category"], widths[2])
        bt   = f"{time_emoji(r['best_time'])} {trunc(r['best_time'], widths[3]-2)}"
        rt   = f"{stars(r['rating'])} {r['rating']:.1f}"
        cst  = cost_emoji(r["cost"])
        print(fmt.format(i, name, cat, bt, rt, cst))
        if r.get("notes"):
            print(f"    💡 Why visit: {r['notes']}")
        print()

# ========= Main =========
async def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n[Hint] Create a .env with: GEMINI_API_KEY=YOUR_KEY\n")
        raise RuntimeError("GEMINI_API_KEY not found in .env")

    model_client = OpenAIChatCompletionClient(
        model="gemini-2.5-flash",
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_info={
            "function_calling": True,
            "vision": False,
            "json_output": False,
            "structured_output": False,
            "family": "gemini",
        },
    )

    print("\n== Attraction Finder & Rating Analyzer == ✈️🗺️")
    print("Type INSIDE this program when prompted. If you press Enter with no text, it will exit.")
    print("If you see the PowerShell prompt (PS C:\\...>), the program has ended.\n")

    # ---- Inputs ----
    city = input("🏙️  City (e.g., Kandy, Paris, Tokyo): ").strip()
    if not city:
        print("Please enter a city.")
        return
    interests = input("🎯 Interests (comma-separated, e.g., temples, museums, nature): ").strip()
    n_free = input("🆓 How many FREE/LOW-COST alternatives to include? (e.g., 3): ").strip()
    try:
        n_free = max(0, int(n_free)) if n_free else 0
    except ValueError:
        print("Please enter a valid integer for number of free/low-cost alternatives.")
        return

    # Safety + PII
    safe_ok, why = policy_gate(" ".join([city, interests, str(n_free)]))
    if not safe_ok:
        print("Blocked for safety:", why)
        return
    interests = redact_pii(interests)

    # ---- Agents ----
    example_attractions_payload = {
        "city": "Example City",
        "interests": ["museums", "temples", "nature"],
        "free_low_cost_count": 2,
        "attractions": [
            {
                "name": "Central History Museum",
                "category": "Museum",
                "best_time": "Nov–Mar (dry / cooler)",
                "notes": "Renowned permanent collection; guided tours; near main transit.",
                "rating": 4.5,
                "cost": "paid"
            },
            {
                "name": "Riverside Promenade",
                "category": "Scenic Walk",
                "best_time": "Sunset; Dec–Feb less humid",
                "notes": "Free riverside walk with food stalls; photo spots.",
                "rating": 4.2,
                "cost": "free"
            }
        ]
    }

    attraction_finder = AssistantAgent(
        name="attraction_finder",
        description="Finds real, public attractions for a city matching interests; includes free/low-cost picks.",
        system_message=(
            "ROLE: Attraction Finder.\n"
            "You MUST propose REAL public attractions that a tourist can actually visit in the given CITY. "
            "Do not invent locations. Prefer well-known, well-reviewed places.\n\n"
            "OUTPUT FORMAT (STRICT):\n"
            "ATTRACTIONS:\njson\n" + json.dumps(example_attractions_payload, ensure_ascii=False, indent=2) + "\n\n"
            "NOTES:\n"
            "- 'best_time' must be concrete (e.g., specific months/seasons or day periods like 'sunrise', 'late afternoon').\n"
            "- 'category' is a concise type (e.g., Temple, Museum, Park, Market, Scenic Viewpoint, Neighborhood).\n"
            "- 'rating' is a 0–5 float synthesized from public consensus.\n"
            "- Include at least the requested number of free/low-cost items (if possible).\n"
            f"Return ONLY the fenced JSON block. End with {END_TOKEN}."
        ),
        model_client=model_client,
    )

    rating_analyzer = AssistantAgent(
        name="rating_analyzer",
        description="Ranks/scores attractions by interest fit, cost preference, and consensus rating.",
        system_message=(
            "ROLE: Rating & Ranking Analyzer.\n"
            "Given ATTRACTIONS JSON with fields (name, category, best_time, notes, rating, cost), "
            "compute a relevance score that blends:\n"
            "  - rating (60%),\n"
            "  - interest/category match (30%),\n"
            "  - free/low-cost preference boost (10%).\n"
            "Then output a sorted list (desc) with the same fields.\n\n"
            "STRICT OUTPUT FORMAT:\n"
            "RATED_LIST:\njson\n"
            "{\n"
            '  "city": "string",\n'
            '  "sorted": [\n'
            "    {\n"
            '      "name": "string",\n'
            '      "category": "string",\n'
            '      "best_time": "string",\n'
            '      "notes": "string",\n'
            '      "rating": 0.0,\n'
            '      "cost": "free|low|paid"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"No commentary before/after the fenced JSON. End with {END_TOKEN}."
        ),
        model_client=model_client,
    )

    # ---- Phase 1: Attraction Finder (with retries) ----
    def finder_task(strict_only=False):
        tighten = "Return ONLY the fenced JSON (no prose)." if strict_only else "Return the fenced JSON."
        return (
            f"CITY: {city}\n"
            f"INTERESTS: {interests}\n"
            f"FREE/LOW-COST COUNT: {n_free}\n\n"
            "Find attractions per your role and output strictly as instructed.\n"
            f"{tighten}"
        )

    found = None
    raw_finder_replies = []
    for attempt in range(3):
        team1 = RoundRobinGroupChat(
            participants=[attraction_finder],
            termination_condition=TextMentionTermination(END_TOKEN),
            max_turns=2,
        )
        convo1 = await team1.run(task=finder_task(strict_only=(attempt >= 1)))
        msg1 = last_from_agent(convo1, "attraction_finder")
        raw_finder_replies.append(msg1)
        found = extract_labeled_json("ATTRACTIONS", msg1)
        if found and isinstance(found.get("attractions"), list) and found["attractions"]:
            break

    if not found:
        print("\n[Attraction Finder JSON parsing failed after 3 attempts]")
        print("Last raw reply (for debugging):\n")
        print(raw_finder_replies[-1] if raw_finder_replies else "(no reply)")
        print("\nPlease try again with broader interests or a more prominent city.")
        return

    base_items = normalize_attractions(found.get("attractions", []))
    if not base_items:
        print("No attractions were returned. Try adjusting your interests.")
        return

    # ---- Phase 2: Rating Analyzer ----
    analyzer_input = {
        "city": city,
        "interests": [s.strip() for s in interests.split(",") if s.strip()],
        "items": base_items
    }
    task2 = (
        "Analyze and rank these attractions:\n"
        "json\n" + json.dumps(analyzer_input, ensure_ascii=False, indent=2) +
        "\nReturn STRICT RATED_LIST JSON (fenced)."
    )

    rated = None
    raw_rate_replies = []
    for attempt in range(2):
        team2 = RoundRobinGroupChat(
            participants=[rating_analyzer],
            termination_condition=TextMentionTermination(END_TOKEN),
            max_turns=2,
        )
        convo2 = await team2.run(task=task2)

        msg2 = last_from_agent(convo2, "rating_analyzer")
        raw_rate_replies.append(msg2)
        rated = extract_labeled_json("RATED_LIST", msg2)
        if rated and isinstance(rated.get("sorted"), list) and rated["sorted"]:
            break

    # Fallback: sort by rating locally
    if not rated or not rated.get("sorted"):
        sorted_items = sorted(base_items, key=lambda r: r.get("rating", 0.0), reverse=True)
    else:
        sorted_items = normalize_attractions(rated["sorted"])

    # ---- Output ----
    print(f"\n--- Top Attractions for {city} ---\n")
    if interests:
        print(f"🎯 Interests: {interests}")
    if n_free:
        print(f"🆓 Requested free/low-cost items: {n_free}")
    print()
    print_table(sorted_items)

if __name__ == "__main__":
    asyncio.run(main())
