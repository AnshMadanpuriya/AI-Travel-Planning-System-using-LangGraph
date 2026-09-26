"""Subprocess-only fixtures: no real provider keys or live network requests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def emit(event):
    print(json.dumps(event), flush=True)


def main():
    mode = sys.argv[1]
    if mode == "heartbeat":
        path = Path(sys.argv[2])
        while True:
            path.write_text(str(time.monotonic()), encoding="utf-8")
            time.sleep(0.05)
    if mode == "hang":
        json.load(sys.stdin)
        subprocess.Popen(
            [sys.executable, __file__, "heartbeat", sys.argv[2]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            start_new_session=os.name != "nt",
        )
        emit({"stage": "Checking flights"})
        emit(
            {
                "tool_result": {
                    "tool": "search_flights",
                    "arguments": {},
                    "status": "success",
                    "result": {"price_inr": 4200, "currency": "INR"},
                }
            }
        )
        time.sleep(60)
    if mode == "answer_then_hang":
        json.load(sys.stdin)
        emit({"result": {"answer": "Completed plan", "partial": False}})
        time.sleep(60)
    if mode == "real_mcp":
        os.environ["GROQ_API_KEY"] = "test-key"
        from langchain_core.messages import AIMessage

        from travel_planner import agent, worker

        class FakeModel:
            def __init__(self, **kwargs):
                self.turn = 0

            def bind_tools(self, *args, **kwargs):
                return self

            async def ainvoke(self, messages, **kwargs):
                self.turn += 1
                if self.turn == 1:
                    return AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "calculate_trip_budget",
                                "id": "budget",
                                "args": {
                                    "days": 3,
                                    "travelers": 2,
                                    "daily_budget_per_person_inr": 2500,
                                },
                                "type": "tool_call",
                            }
                        ],
                        usage_metadata={"input_tokens": 500, "output_tokens": 200, "total_tokens": 700},
                    )
                assert "15000" in messages[-1].content
                return AIMessage(
                    content="Verified calculation: INR 15,000 on-trip budget; flights excluded."
                )

        agent.ChatGroq = FakeModel
        worker.main()


if __name__ == "__main__":
    main()
