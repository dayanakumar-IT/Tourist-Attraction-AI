# team_minimal.py
import os, sys, asyncio, json
from datetime import date
from dotenv import load_dotenv

# --- Load .env BEFORE importing local modules so API keys are visible ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Ensure we can import modules in this folder
sys.path.append(os.path.dirname(__file__))

# --- AutoGen (AgentChat) ---
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

# --- Gemini via OpenAI-compatible client ---
from autogen_ext.models.openai import OpenAIChatCompletionClient

# --- Your local agent logic (modules are in the SAME folder) ---
from schemas import PlannerPayload, ScamWatcherResponse
# Tool wrappers below still use these, which are fine for non-async contexts
from scam_watcher import score_payload as scam_score_payload, score_payload_async
from safety_policy import merge_and_explain as safety_merge_and_explain, merge_and_explain_async


# ---------------------------
# Tool wrappers for AutoGen
# ---------------------------
def tool_score_payload(payload_json: str) -> str:
    """
    Input: JSON string matching PlannerPayload schema.
    Output: ScamWatcherResponse JSON string.
    NOTE: AutoGen calls tools from within an event loop. If your library errors on that,
    switch this to dispatch the async version via asyncio.run_coroutine_threadsafe from a thread.
    For your current mid-eval, the chat path is optional; the fallback below is authoritative.
    """
    payload = PlannerPayload.model_validate_json(payload_json)
    checks = scam_score_payload(payload)  # if this ever errors in your env, remove tool usage and rely on fallback
    return checks.model_dump_json()

def tool_merge_and_explain(planner_json: str, checks_json: str) -> str:
    """
    Inputs:
      - planner_json: PlannerPayload JSON
      - checks_json : ScamWatcherResponse JSON
    Output: SafetyReport JSON string.
    """
    payload = PlannerPayload.model_validate_json(planner_json)
    checks = ScamWatcherResponse.model_validate_json(checks_json)
    report = safety_merge_and_explain(payload, checks)
    return report.model_dump_json()


async def main():
    # 1) Connect to Gemini
    model_client = OpenAIChatCompletionClient(
        model="gemini-2.5-flash",
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_info={
            "function_calling": True,
            "vision": False,
            "json_output": False,
            "structured_output": False,  # quiet a warning
            "family": "gemini",
        },
    )

    # ============================================================
    # A) ORIGINAL TEAM (planner + critic + you)
    # ============================================================
    planner = AssistantAgent(
        name="planner",
        description="Plans itineraries step-by-step with constraints.",
        system_message="Plan clearly in numbered steps. End with DONE.",
        model_client=model_client,
    )
    critic = AssistantAgent(
        name="critic",
        description="Reviews and improves plans.",
        system_message="Review the plan. Suggest fixes if needed. End with DONE.",
        model_client=model_client,
    )
    you = UserProxyAgent(name="you")

    team_plan = RoundRobinGroupChat(
        participants=[you, planner, critic],
        termination_condition=TextMentionTermination("DONE"),
        max_turns=6,
    )

    task = (
        "Create a 1-day Kandy sightseeing plan under 5000 LKR for two students. "
        "Minimize transport cost, include timings, add 2 free/low-cost alternatives. "
        "End with DONE."
    )

    result_plan = await team_plan.run(task=task)

    print("\n================= ORIGINAL TEAM RESULT =================\n")
    print(result_plan.messages[-1].content)

    # ==================================================================
    # B) SAFETY/SCAM TEAM — GET USER INPUT (interactive)
    # ==================================================================
    print("\nEnter trip details for Scam Watcher & Safety Agent:\n")

    try:
        city = input("Enter city (default Kandy): ").strip() or "Kandy"
    except EOFError:
        city = "Kandy"
    try:
        country = input("Enter country code, e.g., LK (default LK): ").strip() or "LK"
    except EOFError:
        country = "LK"

    items = []
    while True:
        try:
            name = input("\nEnter the place to be visited (press Enter to finish): ").strip()
        except EOFError:
            name = ""
        if not name:
            break
        try:
            url = input("Enter the place  URL (e.g., https://...): ").strip()
        except EOFError:
            url = ""
        try:
            price_str = input("Enter place ticket price (blank = unknown): ").strip()
            price = float(price_str) if price_str else None
        except Exception:
            price = None
        try:
            methods = input("Payment methods (comma separated, e.g., cash, card, whatsapp): ").strip()
            methods_list = [m.strip() for m in methods.split(",") if m.strip()]
        except EOFError:
            methods_list = []

        items.append({
            "name": name,
            "url": url,
            "price": price,
            "payment_methods": methods_list
        })

    # If user added nothing, keep a useful demo sample so the agents show signals
    if not items:
        items = [
            {
                "name": "Temple of the Tooth ticket",
                "url": "http://tooth-temple.shop",
                "price": 5.0,
                "payment_methods": ["whatsapp"]
            },
            {
                "name": "Colombo city tuk-tuk tour",
                "url": "https://supercheep-tours.com",
                "price": 8.0,
                "payment_methods": ["cash"]
            }
        ]
        print("\n(No items entered — using demo items so you can see the agents’ output.)")

    example_payload = {
        "city": city,
        "country": country,
        "date": str(date.today()),
        "items": items
    }
    planner_json = json.dumps(example_payload)

    # user proxy for the safety round (unique name; no system_message)
    planner_proxy = UserProxyAgent(name="planner_proxy")

    scamwatch = AssistantAgent(
        name="scamwatch",
        system_message=(
            "You are the Scam Watcher Agent.\n"
            "- When you receive a message containing 'PLANNER_PAYLOAD_JSON:', "
            "extract the JSON that follows and call the tool 'tool_score_payload' "
            "with that JSON string as the only argument.\n"
            "- Then respond ONLY with the tool output (pure JSON). No extra words."
        ),
        model_client=model_client,
        tools=[tool_score_payload],
    )

    safety = AssistantAgent(
        name="safety",
        system_message=(
            "You are the Safety/Policy & Explainability Agent.\n"
            "- When you receive a ScamWatcherResponse JSON, call the tool "
            "'tool_merge_and_explain' using the original planner JSON and the "
            "received checks JSON.\n"
            "- The original planner JSON is always included in the conversation "
            "as PLANNER_PAYLOAD_JSON. Use that exact JSON.\n"
            "- Respond ONLY with the tool output (pure JSON). No extra words."
        ),
        model_client=model_client,
        tools=[tool_merge_and_explain],
    )

    team_safety = RoundRobinGroupChat(
        participants=[planner_proxy, scamwatch, safety],
        termination_condition=TextMentionTermination("SAFETY_DONE"),
        max_turns=6,
    )

    kickoff = (
        "ScamWatch → call tool_score_payload with this planner payload JSON; "
        "Safety → then call tool_merge_and_explain with the SAME planner JSON plus ScamWatcherResponse. "
        "Return the final SafetyReport JSON. When the SafetyReport JSON is visible, I will reply with SAFETY_DONE.\n\n"
        f"PLANNER_PAYLOAD_JSON:\n{planner_json}"
    )

    result_safety = await team_safety.run(task=kickoff)

    print("\n================= SAFETY/SCAM TEAM RESULT =================\n")
    # Print whatever the chat produced (sometimes just the kickoff text)
    final_msg = result_safety.messages[-1]
    print("[Chat output]:", final_msg.content)

    # === FALLBACK: run safety pipeline directly (deterministic, async-safe) ===
    print("\n[Fallback] Running ScamWatcher -> Safety/Policy directly...\n")

    payload = PlannerPayload.model_validate(example_payload)

    # Small debug line so you can verify keys & query:
    ow_has_key = bool(os.getenv("OPENWEATHER_KEY"))
    print(f"[DEBUG] OpenWeather key loaded: {ow_has_key} | City query: {payload.city},{payload.country or ''}")

    checks = await score_payload_async(payload)                 # ✅ async version
    report = await merge_and_explain_async(payload, checks)     # ✅ async version

    # Inject a fallback safety tip if none were returned (so you ALWAYS see something)
    report_dict = report.model_dump()
    if not report_dict.get("safety_tips"):
        report_dict["safety_tips"] = [
            "No major issues reported—follow normal travel safety precautions (keep valuables secure, use verified providers)."
        ]

    print("SAFETY_REPORT_JSON:\n", json.dumps(report_dict, indent=2))

    print("\n============================ DONE ============================\n")

if __name__ == "__main__":
    asyncio.run(main())
