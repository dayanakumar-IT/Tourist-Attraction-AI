from __future__ import annotations

import json
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from .settings import GEMINI_API_KEY, GEMINI_MODEL
from .contracts import TripRequest, TripNormalized, ItineraryBundle
from .agents.pre_agent import normalize_themes, infer_traveler_profile
from .agents.planner_agent import PlannerAgent


def _ensure_keys():
	if not GEMINI_API_KEY:
		raise RuntimeError("GEMINI_API_KEY not configured")


def _normalize_request(input_json: str) -> str:
	data = json.loads(input_json)
	req = TripRequest(**data)
	themes = normalize_themes(req.experiences, req.free_text_interest)
	profile, src = infer_traveler_profile(req.budget.currency, req.traveler_profile_override)
	norm = TripNormalized(**req.model_dump(), themes=themes, traveler_profile=profile, inference_meta={"profile_source": src})
	return json.dumps(norm.model_dump(mode="json"))


def _plan_itineraries(normalized_request_json: str) -> str:
	norm = TripNormalized(**json.loads(normalized_request_json))
	drafts = PlannerAgent().plan(norm)
	bundle = ItineraryBundle(plans=drafts[:3])
	return json.dumps(bundle.model_dump(by_alias=True, mode="json"))


normalize_tool = StructuredTool.from_function(
	name="normalize_request",
	func=_normalize_request,
	description="Normalize TripRequest JSON to TripNormalized JSON with themes and traveler_profile"
)

plan_tool = StructuredTool.from_function(
	name="plan_itineraries",
	func=_plan_itineraries,
	description="Create 1-3 itinerary plans from a TripNormalized JSON; returns ItineraryBundle JSON"
)


def run_multiagent(payload: Dict[str, Any], *, trace: bool = False) -> Dict[str, Any]:
	_ensure_keys()
	# Validate input early
	TripRequest(**payload)

	model = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, temperature=0.1)

	pre_agent = create_react_agent(model, tools=[normalize_tool])
	planner_agent = create_react_agent(model, tools=[plan_tool])

	# 1) PreAgent step
	msg1 = (
		"TripRequest JSON follows. Normalize it. Return JSON only.\n" +
		json.dumps(payload)
	)
	res1 = pre_agent.invoke({"messages": [HumanMessage(content=msg1)]})
	# LangGraph returns a dict with 'messages'
	if isinstance(res1, dict) and res1.get("messages"):
		last_msg = res1["messages"][-1]
		text1 = getattr(last_msg, "content", "")
	else:
		text1 = str(res1)
	if trace:
		print("PreAgent LLM response:", str(text1)[:200])
	# If the LLM didn't return JSON, fallback to direct tool call
	if not (isinstance(text1, str) and text1.strip().startswith("{")):
		text1 = _normalize_request(json.dumps(payload))

	# 2) Planner step
	msg2 = (
		"TripNormalized JSON follows. Plan itineraries. Return JSON only.\n" +
		text1
	)
	res2 = planner_agent.invoke({"messages": [HumanMessage(content=msg2)]})
	if isinstance(res2, dict) and res2.get("messages"):
		last_msg2 = res2["messages"][-1]
		text2 = getattr(last_msg2, "content", "")
	else:
		text2 = str(res2)
	if trace:
		print("PlannerAgent LLM response:", str(text2)[:200])
	if not (isinstance(text2, str) and text2.strip().startswith("{")):
		text2 = _plan_itineraries(text1)

	data = json.loads(text2)
	ItineraryBundle(**data)  # validate
	return data


