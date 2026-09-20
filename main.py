"""Command-line entry point for VoyageGraph MCP."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from travel_planner import plan_trip_sync  # noqa: E402


def run_once(query: str) -> int:
    try:
        result = plan_trip_sync(query)
    except (RuntimeError, ValueError) as error:
        print(f"Configuration error: {error}")
        return 1
    except Exception as error:
        print(f"Planner error: {error}")
        return 1

    print("\n" + result.answer)
    if result.tool_trace:
        names = ", ".join(item["tool"] for item in result.tool_trace)
        print(f"\nMCP tools used: {names}")
    return 0


def interactive_mode() -> int:
    print("VoyageGraph MCP — AI Travel Planner")
    print("Describe a trip, or type 'exit'.\n")
    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if query.lower() in {"exit", "quit"}:
            return 0
        if query:
            run_once(query)
            print()


def main() -> int:
    parser = argparse.ArgumentParser(description="MCP-powered AI travel planner")
    parser.add_argument("query", nargs="*", help="Trip request to plan")
    args = parser.parse_args()
    query = " ".join(args.query).strip()
    return run_once(query) if query else interactive_mode()


if __name__ == "__main__":
    raise SystemExit(main())
