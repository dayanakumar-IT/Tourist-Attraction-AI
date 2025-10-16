import os
import asyncio
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in your .env file")

    # Gemini via Google's OpenAI-compatible endpoint
    model_client = OpenAIChatCompletionClient(
        model=model,
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    # -------- Agents (3 roles) --------
    planner = AssistantAgent(
        name="Planner",
        model_client=model_client,
        system_message=(
            "You are Planner. Always start with 'Planner: '. "
            "Read the task, break it into clear sub-goals, and direct TourGuide on what to draft. "
            "Focus on realistic sequencing (Colombo arrival, travel times, regions). "
            "Keep it concise (3-5 bullets). Do not produce the final itinerary yourself—"
            "ask TourGuide to propose it."
        ),
    )

    tourguide = AssistantAgent(
        name="TourGuide",
        model_client=model_client,
        system_message=(
            "You are TourGuide. Always start with 'TourGuide: '. "
            "Draft a short, realistic, day-by-day Sri Lanka itinerary with iconic places "
            "(e.g., Sigiriya, Kandy, Ella, Galle) starting from Colombo. "
            "Prefer scenic train segments where they make sense (e.g., Kandy→Ella). "
            "Keep each day 2–4 concise bullets; include rough travel times and one local tip."
        ),
    )

    critic = AssistantAgent(
        name="Critic",
        model_client=model_client,
        system_message=(
            "You are Critic. Always start with 'Critic: '. "
            "Evaluate TourGuide's plan for feasibility (not overpacked, sensible routes, realistic times), "
            "safety, and clarity. If fixes are needed, apply them briefly. "
            "When satisfied, output a single line starting with 'FINAL ANSWER: ' containing the polished itinerary."
        ),
    )

    # First participant talks first; then round-robin order
    team = RoundRobinGroupChat(
        participants=[planner, tourguide, critic],
        termination_condition=MaxMessageTermination(max_messages=7),
    )

    # -------- Task (different prompt, still Sri Lanka travel) --------
    task = (
        "Coordinate as a team to propose a compact 3-day Sri Lanka itinerary for a first-time visitor "
        "arriving in Colombo, covering highlights such as Sigiriya, Kandy, Ella, and Galle. "
        "Keep travel realistic (note ~times) and mention the scenic train leg if used. "
        "Planner should assign the drafting to TourGuide; Critic should finalize with 'FINAL ANSWER: ...'."
    )

    result = await team.run(task=task)

    # -------- Pretty print transcript with clear speaker labels --------
    print("\n=== TRANSCRIPT ===")
    final_line = None
    if result and getattr(result, "messages", None):
        for i, m in enumerate(result.messages, 1):
            content = getattr(m, "content", "")
            # Label first line as Task if it matches the seed task
            if i == 1 and content == task:
                who = "Task"
            else:
                # Agents prefix their own outputs; use that for labeling.
                who = content.split(":")[0] if ":" in content else "Agent"
            print(f"[{i:02d}] {who}: {content}")

            if content.strip().startswith("FINAL ANSWER:"):
                final_line = content.strip()

        print("\n=== FINAL OUTPUT ===")
        if final_line:
            print(final_line)
        else:
            # Fallback: last message if FINAL ANSWER wasn't produced for some reason
            print(result.messages[-1].content)
    else:
        print("(No messages returned—check your API key/model).")

if __name__ == "__main__":
    asyncio.run(main())
