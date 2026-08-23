from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .agents import (
    budget_agent,
    final_response_agent,
    flight_agent,
    hotel_agent,
    human_approval_agent,
    itinerary_agent,
    supervisor_agent,
    weather_agent,
)
from .config import settings
from .state import TravelState

AGENT_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]

ROUTE_MAP = {agent: agent for agent in AGENT_ORDER} | {"blocked": "blocked"}
_postgres_connection: Any = None


def _selected(state: TravelState) -> list[str]:
    requested = state.get("selected_agents") or []
    selected = [agent for agent in AGENT_ORDER if agent in requested]
    if "itinerary_agent" not in selected and not state.get("blocked_reason"):
        selected.append("itinerary_agent")
    return selected


def route_from_supervisor(state: TravelState) -> str:
    if state.get("blocked_reason"):
        return "blocked"
    selected = _selected(state)
    return selected[0] if selected else "itinerary_agent"


def route_after(current_agent: str):
    def route(state: TravelState) -> str:
        selected = _selected(state)
        current_index = AGENT_ORDER.index(current_agent)
        for candidate in AGENT_ORDER[current_index + 1 :]:
            if candidate in selected:
                return candidate
        return "itinerary_agent"

    return route


def _checkpointer():
    global _postgres_connection
    if not settings.database_url:
        return MemorySaver()

    import psycopg
    from langgraph.checkpoint.postgres import PostgresSaver

    _postgres_connection = psycopg.connect(settings.database_url, autocommit=True)
    saver = PostgresSaver(_postgres_connection)
    saver.setup()
    return saver


def build_graph(checkpointer=None):
    graph = StateGraph(TravelState)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("flight_agent", flight_agent)
    graph.add_node("hotel_agent", hotel_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("budget_agent", budget_agent)
    graph.add_node("itinerary_agent", itinerary_agent)
    graph.add_node("human_approval", human_approval_agent)
    graph.add_node("final_response", final_response_agent)
    graph.add_node("blocked", lambda state: {})

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route_from_supervisor, ROUTE_MAP)
    graph.add_conditional_edges("flight_agent", route_after("flight_agent"), ROUTE_MAP)
    graph.add_conditional_edges("hotel_agent", route_after("hotel_agent"), ROUTE_MAP)
    graph.add_conditional_edges("weather_agent", route_after("weather_agent"), ROUTE_MAP)
    graph.add_conditional_edges("budget_agent", route_after("budget_agent"), ROUTE_MAP)
    graph.add_edge("itinerary_agent", "human_approval")
    graph.add_edge("human_approval", "final_response")
    graph.add_edge("final_response", END)
    graph.add_edge("blocked", END)
    return graph.compile(checkpointer=checkpointer or _checkpointer())


app = build_graph()
