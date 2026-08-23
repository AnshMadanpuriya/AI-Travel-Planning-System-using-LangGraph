from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from .config import get_llm
from .mcp_client import (
    ProviderUnavailable,
    current_weather,
    forecast,
    list_airlines,
    list_airports,
    tavily_search,
)
from .state import TravelState


def _calls(state: TravelState) -> int:
    return state.get("llm_calls", 0) + 1


async def _llm_text(system: str, prompt: str) -> str | None:
    llm = get_llm()
    if llm is None:
        return None
    response = await llm.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=prompt)]
    )
    return str(response.content)


def _json_object(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        return {}


def _guess_destination(query: str) -> str:
    match = re.search(r"\b(?:to|in|visit)\s+([A-Za-z][A-Za-z .'-]{1,50})", query, re.I)
    if not match:
        return "the destination"
    return re.split(r"\b(?:for|from|under|with|on)\b", match.group(1), maxsplit=1, flags=re.I)[0].strip()


def _blocked_request(query: str) -> str | None:
    if len(query.strip()) < 5:
        return "Please describe the trip you want to plan."
    unsafe = re.search(
        r"(reveal .*?(system|developer) prompt|api[_ -]?key|password|ignore .*?instructions)",
        query,
        re.I,
    )
    if unsafe:
        return "I can help with travel planning, but I cannot process requests for prompts or credentials."
    return None


async def supervisor_agent(state: TravelState) -> dict:
    query = state["user_query"].strip()
    blocked_reason = _blocked_request(query)
    if blocked_reason:
        return {
            "blocked_reason": blocked_reason,
            "selected_agents": [],
            "final_response": blocked_reason,
            "messages": [AIMessage(content=blocked_reason)],
        }

    raw = await _llm_text(
        "You route travel requests. Return strict JSON only.",
        f"""Choose needed agents from flight_agent, hotel_agent, weather_agent,
budget_agent, itinerary_agent. Itinerary is always required.
Return: {{"selected_agents": [], "trip_constraints": {{"destination": "", "origin": "", "duration": "", "budget": "", "travel_style": "", "special_preferences": []}}, "reasoning": ""}}
User request: {query}""",
    )
    parsed = _json_object(raw)
    selected = [
        agent
        for agent in parsed.get("selected_agents", [])
        if agent in {"flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"}
    ]
    if "itinerary_agent" not in selected:
        selected.append("itinerary_agent")
    if not selected or raw is None:
        selected = [
            "flight_agent",
            "hotel_agent",
            "weather_agent",
            "budget_agent",
            "itinerary_agent",
        ]
    constraints = parsed.get("trip_constraints") or {
        "destination": _guess_destination(query),
        "origin": "",
        "duration": "",
        "budget": "",
        "travel_style": "balanced",
        "special_preferences": [],
    }
    if not constraints.get("destination"):
        constraints["destination"] = _guess_destination(query)
    return {
        "selected_agents": selected,
        "trip_constraints": constraints,
        "supervisor_reasoning": parsed.get("reasoning", "Run the specialist agents and prepare a reviewable draft."),
        "messages": [AIMessage(content="Supervisor created the agent plan.")],
        "llm_calls": _calls(state) if raw is not None else state.get("llm_calls", 0),
    }


async def flight_agent(state: TravelState) -> dict:
    destination = str(state.get("trip_constraints", {}).get("destination", ""))
    provider_results = await asyncio.gather(
        list_airports(destination, limit=8),
        list_airlines(limit=8),
        return_exceptions=True,
    )
    airports = "Unavailable" if isinstance(provider_results[0], Exception) else str(provider_results[0])[:3500]
    airlines = "Unavailable" if isinstance(provider_results[1], Exception) else str(provider_results[1])[:3500]
    raw = await _llm_text(
        "You are a cautious flight-planning specialist. Never claim a booking or guaranteed fare.",
        f"User request: {state['user_query']}\nAirports: {airports}\nAirlines: {airlines}\nProvide likely airports, route guidance, duration factors, a non-binding fare range, and booking advice.",
    )
    result = raw or (
        f"Route research for {destination}: compare the nearest practical airports, total travel time, "
        "baggage, arrival time, and change rules. Live provider data was unavailable, so verify all options before payment."
    )
    return {
        "flight_results": result,
        "messages": [AIMessage(content="Flight agent completed.")],
        "llm_calls": _calls(state) if raw is not None else state.get("llm_calls", 0),
    }


async def hotel_agent(state: TravelState) -> dict:
    query = f"best areas and hotels for {state['user_query']}"
    try:
        live = await tavily_search(query)
        research = str(live)[:5500]
    except ProviderUnavailable:
        research = "Live search is not configured."
    except Exception:
        research = "Live search is temporarily unavailable."
    raw = await _llm_text(
        "You are a hotel-area research specialist. Do not claim live availability.",
        f"User request: {state['user_query']}\nResearch: {research}\nRecommend three types of areas to stay, trade-offs, and verification steps.",
    )
    result = raw or (
        "Compare a central transit-connected area, a quieter residential neighborhood, and a value area one stop outside the core. "
        "Check the total stay cost, cancellation rules, recent reviews, and late-arrival access."
    )
    return {"hotel_results": result, "messages": [AIMessage(content="Hotel agent completed.")]}


async def weather_agent(state: TravelState) -> dict:
    destination = str(state.get("trip_constraints", {}).get("destination", ""))
    results = await asyncio.gather(
        current_weather(destination), forecast(destination), return_exceptions=True
    )
    if all(isinstance(item, Exception) for item in results):
        weather_text = "Live weather is unavailable. Recheck 7–10 days before departure and pack adaptable layers."
    else:
        weather_text = f"Current: {results[0]}\nForecast: {results[1]}"
    return {
        "weather_results": weather_text,
        "messages": [AIMessage(content="Weather agent completed.")],
    }


async def budget_agent(state: TravelState) -> dict:
    raw = await _llm_text(
        "You are a practical travel budget analyst. Prices are estimates until verified.",
        f"""User request: {state['user_query']}
Constraints: {state.get('trip_constraints', {})}
Flights: {state.get('flight_results', '')}
Stays: {state.get('hotel_results', '')}
Weather: {state.get('weather_results', '')}
Return cost categories, risk areas, savings ideas, and feasibility.""",
    )
    result = raw or (
        "Suggested allocation: 32% long-distance travel, 30% accommodation, 15% food, "
        "8% local transport, 9% activities, and 6% contingency. Reprice before booking."
    )
    return {
        "budget_results": result,
        "messages": [AIMessage(content="Budget agent completed.")],
        "llm_calls": _calls(state) if raw is not None else state.get("llm_calls", 0),
    }


async def itinerary_agent(state: TravelState) -> dict:
    raw = await _llm_text(
        "You create practical day-by-day itineraries with transfer buffers and no invented availability.",
        f"""Create a reviewable draft for: {state['user_query']}
Constraints: {state.get('trip_constraints', {})}
Flights: {state.get('flight_results', '')}
Hotels: {state.get('hotel_results', '')}
Weather: {state.get('weather_results', '')}
Budget: {state.get('budget_results', '')}""",
    )
    result = raw or (
        "Day 1: arrive, check in, and take a short orientation walk.\n"
        "Day 2: visit the main landmarks with realistic transfer time.\n"
        "Day 3: focus on local culture, food, and one flexible evening.\n"
        "Continue the same balanced rhythm, keeping the final day light for departure."
    )
    return {
        "itinerary": result,
        "approval_request": "Review the draft and approve it or provide specific revision feedback.",
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": _calls(state) if raw is not None else state.get("llm_calls", 0),
    }


def human_approval_agent(state: TravelState) -> dict:
    feedback = interrupt(
        {
            "question": "Do you approve this itinerary?",
            "draft_itinerary": state.get("itinerary", ""),
            "expected_response": {"approved": True, "feedback": "Optional revision feedback"},
        }
    )
    return {
        "approved": bool(feedback.get("approved")),
        "human_feedback": str(feedback.get("feedback", ""))[:1000],
        "messages": [AIMessage(content="Human approval step completed.")],
    }


async def final_response_agent(state: TravelState) -> dict:
    if state.get("blocked_reason"):
        return {"final_response": state["blocked_reason"]}
    raw = await _llm_text(
        "You produce final user-ready travel plans and clearly label estimates.",
        f"""Approved: {state.get('approved')}
Original request: {state.get('user_query')}
Draft: {state.get('itinerary')}
Budget notes: {state.get('budget_results')}
Human feedback: {state.get('human_feedback')}
If not approved, revise the draft using the feedback. Otherwise polish it.""",
    )
    result = raw or state.get("itinerary", "No itinerary was generated.")
    if not state.get("approved") and state.get("human_feedback"):
        result = f"Revision requested: {state['human_feedback']}\n\n{result}"
    return {
        "final_response": result,
        "messages": [AIMessage(content=result)],
        "llm_calls": _calls(state) if raw is not None else state.get("llm_calls", 0),
    }
