from __future__ import annotations

import json
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from settings import GEMINI_API_KEY, GEMINI_MODEL
from contracts import TripRequest, TripNormalized, ItineraryBundle
from agents.pre_agent import normalize_themes, infer_traveler_profile
from agents.planner_agent import PlannerAgent
from agents.weather_aware_planner import WeatherAwarePlanner


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


def _enhance_with_weather_food(itinerary_json: str) -> str:
	"""Enhance itinerary with weather and food recommendations."""
	try:
		itinerary_data = json.loads(itinerary_json)
		weather_food_agent = WeatherFoodAgent()
		
		# Enhance each plan in the itinerary
		enhanced_plans = []
		for plan in itinerary_data.get("plans", []):
			enhanced_plan = weather_food_agent.enhance_itinerary(plan)
			enhanced_plans.append(enhanced_plan)
		
		enhanced_bundle = {"plans": enhanced_plans}
		return json.dumps(enhanced_bundle)
	except Exception as e:
		# Return original if enhancement fails
		return itinerary_json


def _optimize_transport(itinerary_json: str, group_size: int = 1, budget_currency: str = "LKR") -> str:
	"""Optimize transportation for the itinerary."""
	try:
		itinerary_data = json.loads(itinerary_json)
		transport_agent = TransportAgent()
		
		# Optimize transport for each plan
		optimized_plans = []
		for plan in itinerary_data.get("plans", []):
			optimized_plan = transport_agent.optimize_itinerary_transport(
				plan, group_size, budget_currency
			)
			optimized_plans.append(optimized_plan)
		
		optimized_bundle = {"plans": optimized_plans}
		return json.dumps(optimized_bundle)
	except Exception as e:
		# Return original if optimization fails
		return itinerary_json


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

weather_food_tool = StructuredTool.from_function(
	name="enhance_with_weather_food",
	func=_enhance_with_weather_food,
	description="Enhance itinerary with weather forecasts and food recommendations"
)

transport_tool = StructuredTool.from_function(
	name="optimize_transport",
	func=_optimize_transport,
	description="Optimize transportation routes and costs for the itinerary"
)


def run_multiagent(payload: Dict[str, Any], *, trace: bool = False) -> Dict[str, Any]:
	_ensure_keys()
	# Validate input early
	TripRequest(**payload)

	model = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, temperature=0.1)

	pre_agent = create_react_agent(model, tools=[normalize_tool])
	planner_agent = create_react_agent(model, tools=[plan_tool])
	weather_food_agent = create_react_agent(model, tools=[weather_food_tool])
	transport_agent = create_react_agent(model, tools=[transport_tool])

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
		"You are a travel planner. Create 3 diverse itineraries from the TripNormalized JSON. Use the plan_itineraries tool to generate the itineraries. Return JSON only.\n" +
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

	# 3) Weather & Food enhancement step
	msg3 = (
		"You are a weather and food specialist. Enhance the itinerary with weather forecasts and restaurant recommendations. Use the enhance_with_weather_food tool. Return JSON only.\n" +
		text2
	)
	res3 = weather_food_agent.invoke({"messages": [HumanMessage(content=msg3)]})
	if isinstance(res3, dict) and res3.get("messages"):
		last_msg3 = res3["messages"][-1]
		text3 = getattr(last_msg3, "content", "")
	else:
		text3 = str(res3)
	if trace:
		print("WeatherFoodAgent LLM response:", str(text3)[:200])
	if not (isinstance(text3, str) and text3.strip().startswith("{")):
		text3 = _enhance_with_weather_food(text2)
	
	# Ensure we have enhanced data by calling the tool directly if needed
	try:
		enhanced_data = json.loads(text3)
		if not enhanced_data.get("plans") or not any(
			any("weather_info" in activity or "nearby_restaurants" in activity 
				for activity in day.get("activities", []))
			for plan in enhanced_data.get("plans", [])
			for day in plan.get("daily_plan", [])
		):
			# If no enhanced data, call the tool directly
			text3 = _enhance_with_weather_food(text2)
	except:
		# If parsing fails, call the tool directly
		text3 = _enhance_with_weather_food(text2)

	# 4) Transport optimization step
	group_size = payload.get("party", {}).get("count", 1)
	budget_currency = payload.get("budget", {}).get("currency", "LKR")
	msg4 = (
		f"You are a transportation specialist. Optimize transportation routes and costs for group size {group_size} and currency {budget_currency}. Use the optimize_transport tool. Return JSON only.\n" +
		text3
	)
	res4 = transport_agent.invoke({"messages": [HumanMessage(content=msg4)]})
	if isinstance(res4, dict) and res4.get("messages"):
		last_msg4 = res4["messages"][-1]
		text4 = getattr(last_msg4, "content", "")
	else:
		text4 = str(res4)
	if trace:
		print("TransportAgent LLM response:", str(text4)[:200])
	if not (isinstance(text4, str) and text4.strip().startswith("{")):
		text4 = _optimize_transport(text3, group_size, budget_currency)
	
	# Ensure we have transport data by calling the tool directly if needed
	try:
		transport_data = json.loads(text4)
		if not transport_data.get("plans") or not any(
			any("estimated_cost" in leg or "cost_currency" in leg
				for leg in day.get("travel_legs", []))
			for plan in transport_data.get("plans", [])
			for day in plan.get("daily_plan", [])
		):
			# If no transport data, call the tool directly
			text4 = _optimize_transport(text3, group_size, budget_currency)
	except:
		# If parsing fails, call the tool directly
		text4 = _optimize_transport(text3, group_size, budget_currency)

	# Parse the final result and ensure enhancements are included
	try:
		# Try to get the most enhanced result (transport agent)
		data = json.loads(text4)
		plans = data.get("plans", []) or data.get("optimized_itineraries", [])
		
		# If no plans from transport agent, try weather agent result
		if not plans:
			data = json.loads(text3)
			plans = data.get("plans", [])
		
		# If still no plans, use planner result
		if not plans:
			data = json.loads(text2)
			plans = data.get("plans", []) or data.get("itineraries", [])
		
		# Ensure we have plans and limit to 1 (single optimized plan)
		if plans:
			data["plans"] = plans[:1]  # Only return the best plan
		else:
			# Fallback: create basic plans from planner
			fallback_data = json.loads(text2)
			data = fallback_data
			if "plans" in data:
				data["plans"] = data["plans"][:1]  # Only return the best plan
			elif "itineraries" in data:
				data["plans"] = data["itineraries"][:1]  # Only return the best plan
		
		# Always force the tool calls to ensure enhanced data is included
		print("Forcing weather/food enhancement...")
		try:
			enhanced_json = _enhance_with_weather_food(json.dumps(data))
			enhanced_data = json.loads(enhanced_json)
			data = enhanced_data
			print("Weather/food enhancement successful")
		except Exception as e:
			print(f"Weather/food enhancement failed: {e}")
		
		print("Forcing transport optimization...")
		try:
			group_size = payload.get("party", {}).get("count", 1)
			budget_currency = payload.get("budget", {}).get("currency", "LKR")
			optimized_json = _optimize_transport(json.dumps(data), group_size, budget_currency)
			optimized_data = json.loads(optimized_json)
			data = optimized_data
			print("Transport optimization successful")
		except Exception as e:
			print(f"Transport optimization failed: {e}")
		
		print("Adapting to weather conditions...")
		try:
			weather_planner = WeatherAwarePlanner()
			adapted_plans = []
			for plan in data.get("plans", []):
				adapted_plan = weather_planner.adapt_itinerary_to_weather(plan)
				adapted_plans.append(adapted_plan)
			data["plans"] = adapted_plans
			print("Weather adaptation successful")
		except Exception as e:
			print(f"Weather adaptation failed: {e}")
		
		print("Validating final result...")
		try:
			ItineraryBundle(**data)  # validate
			print("Validation successful")
		except Exception as e:
			print(f"Validation failed: {e}")
			# If validation fails, try to fix the data structure
			if "plans" not in data:
				data = {"plans": []}
		
		return data
		
	except Exception as e:
		# If all else fails, return the planner result
		try:
			data = json.loads(text2)
			if "plans" in data:
				data["plans"] = data["plans"][:2]
			elif "itineraries" in data:
				data["plans"] = data["itineraries"][:2]
			return data
		except:
			# Last resort: return empty result
			return {"plans": []}


