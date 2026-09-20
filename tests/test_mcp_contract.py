from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import Client
from langchain_groq import ChatGroq

from mcp_server import mcp
from travel_planner.agent import _mcp_tool_to_schema

EXPECTED_TOOLS = {
    "search_flights",
    "search_hotels",
    "get_weather_forecast",
    "search_destination_guides",
    "create_itinerary",
    "calculate_trip_budget",
}


async def _exercise_mcp_server() -> tuple[list[Any], Any]:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        result = await client.call_tool(
            "calculate_trip_budget",
            {
                "days": 3,
                "travelers": 2,
                "daily_budget_per_person_inr": 2_500,
            },
        )
    return tools, result


def test_mcp_server_exposes_expected_contract() -> None:
    tools, result = asyncio.run(_exercise_mcp_server())
    tool_map = {tool.name: tool for tool in tools}

    assert set(tool_map) == EXPECTED_TOOLS
    flight_schema = tool_map["search_flights"].input_schema
    assert {"origin", "destination", "departure_date"}.issubset(set(flight_schema["required"]))

    budget_data = getattr(result, "data", None) or getattr(result, "structured_content", None)
    assert budget_data["on_trip_budget_inr"] == 15_000

    schemas = [_mcp_tool_to_schema(tool) for tool in tools]
    model = ChatGroq(api_key="test-key", model="openai/gpt-oss-120b")
    bound_model = model.bind_tools(schemas, parallel_tool_calls=False)
    assert bound_model is not None
