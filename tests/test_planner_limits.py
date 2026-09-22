from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from fastmcp import Client
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq

from travel_planner import agent
from travel_planner.config import Settings
from travel_planner.payloads import byte_size, compact_result


class ProviderError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__("Private provider account information must not reach the UI")


def response(text: str = "", calls: list | None = None) -> AIMessage:
    return AIMessage(
        content=text,
        tool_calls=calls or [],
        usage_metadata={
            "input_tokens": 500,
            "output_tokens": 200,
            "total_tokens": 700,
        },
    )


def call(name: str, call_id: str, **arguments) -> dict:
    return {"name": name, "id": call_id, "args": arguments, "type": "tool_call"}


def install_fakes(monkeypatch, responses, *, tool_handler=None, timeout=55):
    recorded = []
    executed = []
    construction = []
    outcomes = iter(responses)
    settings = replace(
        Settings.from_env(), groq_api_key="test-key", planner_timeout_seconds=timeout
    )
    monkeypatch.setattr(agent.Settings, "from_env", classmethod(lambda cls: settings))

    class FakeModel:
        def __init__(self, **kwargs):
            construction.append(kwargs)

        def bind_tools(self, schemas, **kwargs):
            assert kwargs["parallel_tool_calls"] is True
            return self

        async def ainvoke(self, messages, **kwargs):
            recorded.append((messages, kwargs))
            outcome = next(outcomes)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    class FakeClient:
        def __init__(self, path):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def list_tools(self):
            return [
                SimpleNamespace(
                    name=name, description=name, input_schema={"type": "object", "properties": {}}
                )
                for name in [
                    "search_flights",
                    "search_hotels",
                    "get_weather_forecast",
                    "create_itinerary",
                    "calculate_trip_budget",
                    "search_destination_guides",
                ]
            ]

        async def call_tool(self, name, arguments):
            executed.append((name, arguments))
            data = (
                await tool_handler(name, arguments)
                if tool_handler
                else {
                    "source": "test provider",
                    "price_inr": 12345,
                    "currency": "INR",
                    "note": "total for two adults; excludes baggage",
                }
            )
            return SimpleNamespace(data=data, is_error=False)

    monkeypatch.setattr(agent, "ChatGroq", FakeModel)
    monkeypatch.setattr(agent, "Client", FakeClient)
    return recorded, executed, construction


def test_two_calls_parallel_tools_and_duplicate_suppression(monkeypatch):
    started = set()
    ready = asyncio.Event()

    async def handler(name, args):
        started.add(name)
        if len(started) == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), 0.5)
        return {"source": name, "currency": "INR", "price": 12345}

    recorded, executed, construction = install_fakes(
        monkeypatch,
        [
            response(
                calls=[
                    call("search_flights", "a", origin="DEL", destination="GOI"),
                    call("search_hotels", "b", destination="Goa"),
                    call("search_flights", "c", origin="DEL", destination="GOI"),
                ]
            ),
            response("Flights and hotels checked."),
        ],
        tool_handler=handler,
    )
    result = asyncio.run(agent.plan_trip("Plan a trip to Goa"))
    assert not result.partial
    assert result.answer == "Flights and hotels checked."
    assert len(recorded) == 2
    assert len(executed) == 2
    assert all(kwargs["max_completion_tokens"] <= 1536 for _, kwargs in recorded)
    assert construction[0]["max_retries"] == 0
    assert construction[0]["reasoning_effort"] == "low"
    assert all(not getattr(msg, "tool_calls", None) for msg in recorded[-1][0])


def test_413_retries_once_with_smaller_payload(monkeypatch):
    recorded, _, _ = install_fakes(monkeypatch, [ProviderError(413), response("Which dates?")])
    history = [
        {"role": "user", "content": "Old brief " * 500},
        {"role": "assistant", "content": "Old answer " * 500},
    ]
    result = asyncio.run(agent.plan_trip("Goa please", history))
    assert result.answer == "Which dates?"
    assert len(recorded) == 2
    assert len(recorded[1][0]) < len(recorded[0][0])
    assert recorded[1][1]["max_completion_tokens"] < recorded[0][1]["max_completion_tokens"]


@pytest.mark.parametrize("status", [413, 429])
def test_rate_limit_returns_actual_completed_results(monkeypatch, status):
    outcomes = [response(calls=[call("search_flights", "a")]), ProviderError(status)]
    if status == 413:
        outcomes.append(ProviderError(413))
    recorded, executed, _ = install_fakes(monkeypatch, outcomes)
    result = asyncio.run(agent.plan_trip("Search flights to Goa"))
    assert result.partial
    assert "12345" in result.answer
    assert "excludes baggage" in result.answer
    assert "not a complete itinerary" in result.answer
    assert "Private provider" not in result.answer
    assert len(executed) == 1
    assert len(recorded) == (3 if status == 413 else 2)


def test_slow_tool_does_not_discard_completed_search(monkeypatch):
    async def handler(name, args):
        if name == "search_hotels":
            await asyncio.Event().wait()
        return {"source": "checked flights", "price_inr": 4000}

    install_fakes(
        monkeypatch,
        [
            response(calls=[call("search_flights", "a"), call("search_hotels", "b")]),
            response("Flights found. Hotels could not be verified."),
        ],
        tool_handler=handler,
        timeout=15.1,
    )
    result = asyncio.run(agent.plan_trip("Goa flights and hotels"))
    assert result.partial
    assert result.elapsed_seconds < 1
    statuses = {item["tool"]: item["status"] for item in result.tool_trace}
    assert statuses == {"search_flights": "success", "search_hotels": "error"}


def test_deadline_includes_mcp_startup(monkeypatch):
    install_fakes(monkeypatch, [], timeout=0.05)

    class HangingClient:
        def __init__(self, path):
            pass

        async def __aenter__(self):
            await asyncio.Event().wait()

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(agent, "Client", HangingClient)
    result = asyncio.run(agent.plan_trip("Goa trip"))
    assert result.partial and result.elapsed_seconds < 1
    assert "time limit" in result.answer


def test_compaction_keeps_prices_scope_and_original_data():
    data = {
        "source": "provider",
        "currency": "INR",
        "price_scope": "two adults",
        "verification_note": "Excludes baggage",
        "offers": [
            {
                "price_inr": 12000 + i,
                "flight_numbers": ["A1", "B2"],
                "url": "https://example.com/flight",
                "description": "x" * 200,
            }
            for i in range(30)
        ],
    }
    small = compact_result(data, 1500)
    assert byte_size(small) <= 1500
    assert len(data["offers"]) == 30
    assert small["offers"][0] == data["offers"][0]
    assert small["currency"] == "INR"
    assert small["price_scope"] == "two adults"
    assert small["verification_note"] == "Excludes baggage"
    assert "omitted" in small["payload_note"]


def test_long_history_and_large_results_are_bounded(monkeypatch):
    async def handler(name, args):
        return {
            "source": name,
            "offers": [{"price_inr": i, "details": "y" * 400} for i in range(100)],
        }

    recorded, _, _ = install_fakes(
        monkeypatch,
        [response(calls=[call("search_flights", "a")]), response("Plan")],
        tool_handler=handler,
    )
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": "गोवा" * 5000} for i in range(20)
    ]
    result = asyncio.run(agent.plan_trip("Plan a Goa trip", history))
    assert not result.partial
    assert len(result.tool_trace[0]["result"]["offers"]) == 100
    assert sum(len(str(msg.content).encode("utf-8")) for msg in recorded[-1][0]) < 13000
    assert len(agent._history_messages(history)) == 3


def test_actual_groq_request_serializes_completion_cap():
    payloads = []

    def handle(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 1,
                "model": "openai/gpt-oss-120b",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            },
        )

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            model = ChatGroq(
                api_key="test-key",
                model="openai/gpt-oss-120b",
                reasoning_effort="low",
                max_retries=0,
                http_async_client=client,
            )
            await model.ainvoke([HumanMessage(content="Hello")], max_completion_tokens=1024)

    asyncio.run(exercise())
    assert payloads[0]["max_completion_tokens"] == 1024
    assert payloads[0]["reasoning_effort"] == "low"


def test_exhausted_local_budget_does_not_make_another_api_request(monkeypatch):
    selection = response(calls=[call("search_flights", "a")])
    selection.usage_metadata = {"input_tokens": 5800, "output_tokens": 1200, "total_tokens": 7000}
    recorded, executed, _ = install_fakes(monkeypatch, [selection])
    result = asyncio.run(agent.plan_trip("Goa flights"))
    assert result.partial
    assert "remaining token budget" in result.answer
    assert len(recorded) == 1 and len(executed) == 1


def test_real_stdio_mcp_tools_with_simulated_model(monkeypatch):
    install_fakes(
        monkeypatch,
        [
            response(
                calls=[
                    call(
                        "calculate_trip_budget",
                        "a",
                        days=3,
                        travelers=2,
                        daily_budget_per_person_inr=2500,
                    ),
                    call("create_itinerary", "b", destination="Goa", days=3),
                ]
            ),
            response("On-trip budget estimate: INR 15,000. Flights excluded."),
        ],
    )
    monkeypatch.setattr(agent, "Client", Client)
    result = asyncio.run(
        agent.plan_trip("Plan three days in Goa for two people at INR 2500 per person per day")
    )
    assert not result.partial, result.answer
    records = {item["tool"]: item["result"] for item in result.tool_trace}
    assert records["calculate_trip_budget"]["on_trip_budget_inr"] == 15000
    assert len(records["create_itinerary"]["itinerary"]) == 3
