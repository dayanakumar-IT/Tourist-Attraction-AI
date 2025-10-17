from __future__ import annotations

import json
from typing import Any, Dict, List

from pydantic import BaseModel

from .contracts import TripRequest, TripNormalized, Itinerary, DayPlan, Activity, TravelLeg, BudgetSummary, ItineraryBundle
from .agents.pre_agent import normalize_themes, infer_traveler_profile
from .agents.planner_agent import PlannerAgent


class GraphState(BaseModel):
	request: TripRequest
	normalized: TripNormalized | None = None
	drafts: List[Itinerary] | None = None
	result: ItineraryBundle | None = None
	trace: List[str] = []


def node_preagent(state: GraphState) -> GraphState:
	req = state.request
	themes = normalize_themes(req.experiences, req.free_text_interest)
	profile, src = infer_traveler_profile(req.budget.currency, req.traveler_profile_override)
	norm = TripNormalized(**req.model_dump(), themes=themes, traveler_profile=profile, inference_meta={"profile_source": src})
	state.normalized = norm
	state.trace.append(f"PreAgent: themes={themes} profile={profile}")
	return state


def node_planner(state: GraphState) -> GraphState:
	assert state.normalized is not None
	planner = PlannerAgent()
	drafts = planner.plan(state.normalized)
	state.drafts = drafts
	state.trace.append(f"PlannerAgent: drafted={len(drafts)}")
	state.result = ItineraryBundle(plans=drafts[:3])
	return state


def run_graph(payload: Dict[str, Any], *, trace: bool = False) -> Dict[str, Any]:
	# Validate request
	req = TripRequest(**payload)
	state = GraphState(request=req)
	# Simple 2-node pipeline (LangGraph-like sequencing)
	state = node_preagent(state)
	state = node_planner(state)
	if trace:
		for line in state.trace:
			print(line)
	return state.result.model_dump(by_alias=True)


