from __future__ import annotations

import sys
import time
from pathlib import Path

from travel_planner.runner import _run_worker

FIXTURE = str(Path(__file__).parent / "fixtures" / "planner_worker.py")


def test_watchdog_returns_partial_results_and_stops_child_process(tmp_path):
    heartbeat = tmp_path / "heartbeat.txt"
    updates = []
    started = time.monotonic()
    result = _run_worker(
        [sys.executable, "-u", FIXTURE, "hang", str(heartbeat)],
        {"query": "Goa"},
        2,
        updates.append,
    )
    assert time.monotonic() - started < 6
    assert result.partial
    assert "4200" in result.answer
    assert "checking flights" in result.answer
    assert any(item["elapsed_seconds"] >= 0.5 for item in updates)
    assert heartbeat.exists(), "Child process must have started for this test to be meaningful"
    last_tick = heartbeat.read_text(encoding="utf-8")
    time.sleep(0.2)
    assert heartbeat.read_text(encoding="utf-8") == last_tick, "The request's child process leaked"


def test_answer_does_not_wait_for_worker_shutdown():
    started = time.monotonic()
    result = _run_worker([sys.executable, "-u", FIXTURE, "answer_then_hang"], {"query": "Goa"}, 10)
    assert result.answer == "Completed plan" and not result.partial
    assert time.monotonic() - started < 5


def test_worker_protocol_and_real_mcp_emit_live_stages():
    updates = []
    result = _run_worker(
        [sys.executable, "-u", FIXTURE, "real_mcp"],
        {"query": "Goa for three days, two adults, INR 2500 per person per day"},
        40,
        updates.append,
    )
    assert not result.partial, result.answer
    assert "15,000" in result.answer
    assert result.tool_trace[0]["result"]["on_trip_budget_inr"] == 15000
    stages = {item["stage"] for item in updates}
    assert "Starting the local MCP server" in stages
    assert "Discovering travel tools" in stages
    assert "Asking Groq to select the travel searches" in stages
    assert "Completed calculate trip budget" in stages
    assert "Writing your plan from the collected results" in stages
