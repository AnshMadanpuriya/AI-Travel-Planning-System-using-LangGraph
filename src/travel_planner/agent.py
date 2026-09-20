"""LangGraph ReAct loop that discovers and executes tools through MCP."""

from __future__ import annotations

import asyncio
import json
import operator
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Literal, TypedDict

from fastmcp import Client
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from .config import Settings

SYSTEM_PROMPT = """You are VoyageGraph, a careful AI travel-planning agent connected to MCP tools.
Today is {today}.

Tool policy:
- Use MCP results as the primary source of truth. Use user-provided facts second.
- For live flight or hotel requests, call the matching MCP tool whenever the required fields exist.
- For a round trip, call search_flights twice: outbound first, then reversed cities on the return date.
- Use weather only for dates returned by the weather tool. Never present current weather as a future forecast.
- Use destination research for attractions, entry rules, or current travel guidance.
- Use the itinerary and budget tools when their required values are known.
- Ask one short clarification question if essential information is missing.
- Never repeat an identical tool call.

Accuracy policy:
- Never invent fares, hotel prices, schedules, ratings, availability, booking links, opening hours,
  visa rules, or cancellation terms.
- Preserve currencies and price scope exactly as returned by tools.
- Treat flight and hotel results as search-time snapshots, not booking guarantees.
- When a tool fails, state what could not be verified and continue with clearly labelled general advice.
- Label unsupported attraction ideas as "AI suggestion — live verification required".

Answer format when enough information is available:
1. Trip snapshot
2. Best flight options
3. Recommended stays
4. Weather and packing notes
5. Day-by-day itinerary
6. Budget view
7. Verify before booking

Only show relevant sections. Write in clear, professional English with compact tables and bullets.
Do not mention internal prompts, schemas, or raw tool JSON.
"""


class PlannerState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    tool_trace: Annotated[list[dict[str, Any]], operator.add]
    steps: int


@dataclass(frozen=True)
class PlannerResult:
    answer: str
    tool_trace: list[dict[str, Any]]
    available_tools: list[str]


def _mcp_tool_to_schema(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
    if schema is None:
        schema = {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "MCP travel tool",
            "parameters": schema,
        },
    }


def _extract_tool_result(result: Any) -> Any:
    data = getattr(result, "data", None)
    if data is not None:
        return data

    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured

    content = getattr(result, "content", None)
    if content:
        values: list[Any] = []
        for item in content:
            text = getattr(item, "text", None)
            values.append(text if text is not None else str(item))
        if len(values) == 1:
            try:
                return json.loads(values[0])
            except (TypeError, json.JSONDecodeError):
                return values[0]
        return values

    return {"error": "The MCP tool returned no readable content."}


def _message_text(message: AnyMessage) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content
        ).strip()
    return str(content).strip()


def _history_messages(history: Sequence[dict[str, str]] | None) -> list[AnyMessage]:
    converted: list[AnyMessage] = []
    for item in list(history or [])[-8:]:
        role = item.get("role")
        content = item.get("content", "").strip()
        if not content:
            continue
        if role == "assistant":
            converted.append(AIMessage(content=content))
        elif role == "user":
            converted.append(HumanMessage(content=content))
    return converted


async def plan_trip(
    query: str,
    history: Sequence[dict[str, str]] | None = None,
) -> PlannerResult:
    """Plan a trip with a LangGraph loop and a local stdio MCP server."""

    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Please describe the trip you want to plan.")

    settings = Settings.from_env()
    settings.require_agent_key()

    async with Client(settings.mcp_server_path) as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        tool_schemas = [_mcp_tool_to_schema(tool) for tool in mcp_tools]
        available_tools = [tool.name for tool in mcp_tools]

        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.1,
            max_retries=2,
        )
        tool_llm = llm.bind_tools(tool_schemas, parallel_tool_calls=False)

        async def agent_node(state: PlannerState) -> dict[str, Any]:
            response = await tool_llm.ainvoke(state["messages"])
            return {"messages": [response]}

        async def tool_node(state: PlannerState) -> dict[str, Any]:
            last_message = state["messages"][-1]
            tool_messages: list[ToolMessage] = []
            trace: list[dict[str, Any]] = []

            for call in getattr(last_message, "tool_calls", []) or []:
                name = call.get("name", "unknown_tool")
                arguments = call.get("args", {}) or {}
                call_id = call.get("id", name)
                try:
                    raw_result = await mcp_client.call_tool(name, arguments)
                    result = _extract_tool_result(raw_result)
                    status = (
                        "error" if isinstance(result, dict) and result.get("error") else "success"
                    )
                except Exception as exc:  # MCP/API failures must return to the model safely.
                    result = {"error": f"{name} could not be completed: {exc}"}
                    status = "error"

                tool_messages.append(
                    ToolMessage(
                        content=json.dumps(result, ensure_ascii=False, default=str),
                        tool_call_id=call_id,
                        name=name,
                    )
                )
                trace.append({"tool": name, "arguments": arguments, "status": status})

            return {
                "messages": tool_messages,
                "tool_trace": trace,
                "steps": state.get("steps", 0) + 1,
            }

        async def finalizer_node(state: PlannerState) -> dict[str, Any]:
            reminder = HumanMessage(
                content=(
                    "Stop calling tools. Produce the best grounded final answer now using only the "
                    "verified information already present. Clearly disclose anything unavailable."
                )
            )
            response = await llm.ainvoke([*state["messages"], reminder])
            return {"messages": [response]}

        def route_after_agent(state: PlannerState) -> Literal["tools", "finalize", "end"]:
            last_message = state["messages"][-1]
            if not getattr(last_message, "tool_calls", None):
                return "end"
            if state.get("steps", 0) >= settings.max_agent_steps:
                return "finalize"
            return "tools"

        workflow = StateGraph(PlannerState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)
        workflow.add_node("finalize", finalizer_node)
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            route_after_agent,
            {"tools": "tools", "finalize": "finalize", "end": END},
        )
        workflow.add_edge("tools", "agent")
        workflow.add_edge("finalize", END)
        graph = workflow.compile()

        initial_messages: list[AnyMessage] = [
            SystemMessage(content=SYSTEM_PROMPT.format(today=date.today().isoformat())),
            *_history_messages(history),
            HumanMessage(content=clean_query),
        ]
        result = await graph.ainvoke({"messages": initial_messages, "tool_trace": [], "steps": 0})

    answer = _message_text(result["messages"][-1])
    if not answer:
        answer = "I could not generate a final plan. Please try again with exact cities and dates."
    return PlannerResult(
        answer=answer,
        tool_trace=result.get("tool_trace", []),
        available_tools=available_tools,
    )


def plan_trip_sync(
    query: str,
    history: Sequence[dict[str, str]] | None = None,
) -> PlannerResult:
    """Synchronous wrapper used by Streamlit and the CLI."""

    return asyncio.run(plan_trip(query=query, history=history))
