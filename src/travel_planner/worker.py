"""Private JSON-lines protocol between the UI watchdog and planner."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from typing import Any


def emit(event: dict[str, Any]) -> None:
    print(json.dumps(event, ensure_ascii=False, default=str), flush=True)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        emit({"stage": "Loading the travel planner"})
        from .agent import plan_trip

        result = asyncio.run(plan_trip(payload["query"], payload.get("history"), on_progress=emit))
        emit({"result": asdict(result)})
    except (RuntimeError, ValueError):
        emit(
            {"error": "The planner could not start. Check your API configuration and restart with uv run."}
        )
    except Exception:
        emit({"error": "The planner process could not finish. Completed checks have been retained."})


if __name__ == "__main__":
    main()
