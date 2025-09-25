# team_minimal.py
import os, asyncio
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

from autogen_ext.models.openai import OpenAIChatCompletionClient

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

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
            "structured_output": False,  # add this to silence the warning
            "family": "gemini",
        },
    )

    # 2) Agents
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

    # 3) Team (no UI arg in this version)
    team = RoundRobinGroupChat(
        participants=[you, planner, critic],
        termination_condition=TextMentionTermination("DONE"),
        max_turns=6,
    )

    # 4) Run
    task = (
        "Create a 1-day Kandy sightseeing plan under 5000 LKR for two students. "
        "Minimize transport cost, include timings, add 2 free/low-cost alternatives. "
        "End with DONE."
    )
    result = await team.run(task=task)

    print("\n--- Final Output ---\n")
    print(result.messages[-1].content)

if __name__ == "__main__":
    asyncio.run(main())
