"""VoyageGraph MCP travel planner package."""

from .models import PlannerResult
from .runner import plan_trip_sync


async def plan_trip(query, history=None, **kwargs):
    """Load the agent only when async planning is requested."""
    from .agent import plan_trip as run

    return await run(query, history, **kwargs)


__all__ = ["PlannerResult", "plan_trip", "plan_trip_sync"]
