from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Travel Aviation")
BASE_URL = "https://api.aviationstack.com/v1"


def _key() -> str:
    key = os.getenv("AVIATION_STACK_API_KEY") or os.getenv("AVIATIONSTACK_API_KEY")
    if not key:
        raise ValueError("AVIATION_STACK_API_KEY is not configured")
    return key


def _list(endpoint: str, search: str, limit: int, offset: int) -> list[dict]:
    response = httpx.get(
        f"{BASE_URL}/{endpoint}",
        params={
            "access_key": _key(),
            "search": search,
            "limit": max(1, min(limit, 25)),
            "offset": max(0, offset),
        },
        timeout=12.0,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"].get("message", "AviationStack request failed"))
    return payload.get("data", [])


@mcp.tool()
def list_airports(search: str = "", limit: int = 10, offset: int = 0) -> list[dict]:
    """Find airports by city, country, airport name, or code."""
    return _list("airports", search, limit, offset)


@mcp.tool()
def list_airlines(search: str = "", limit: int = 10, offset: int = 0) -> list[dict]:
    """Find airlines by name or code."""
    return _list("airlines", search, limit, offset)


if __name__ == "__main__":
    mcp.run()
