"""Lightweight data shared by the UI and the isolated planner process."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlannerResult:
    answer: str
    tool_trace: list[dict[str, Any]]
    available_tools: list[str]
    partial: bool = False
    elapsed_seconds: float = 0.0
