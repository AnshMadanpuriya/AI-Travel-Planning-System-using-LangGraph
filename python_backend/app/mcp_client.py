from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from .config import settings


class ProviderUnavailable(RuntimeError):
    """Raised when an optional live provider is not configured."""


SERVER_DIR = Path(__file__).resolve().parent / "mcp_servers"


def _stdio_env(**values: str | None) -> dict[str, str]:
    env = dict(os.environ)
    env.update({key: value for key, value in values.items() if value})
    return env


async def _call(server_name: str, server_config: dict[str, Any], tool_name: str, args: dict) -> Any:
    client = MultiServerMCPClient({server_name: server_config})
    tools = await client.get_tools()
    tool = next((candidate for candidate in tools if candidate.name == tool_name), None)
    if tool is None:
        raise ProviderUnavailable(f"MCP tool '{tool_name}' is unavailable")
    return await tool.ainvoke(args)


async def tavily_search(query: str) -> Any:
    if not settings.tavily_api_key:
        raise ProviderUnavailable("TAVILY_API_KEY is not configured")
    return await _call(
        "tavily",
        {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={settings.tavily_api_key}",
        },
        "tavily_search",
        {"query": query},
    )


async def list_airports(search: str, limit: int = 8) -> Any:
    if not settings.aviation_stack_api_key:
        raise ProviderUnavailable("AVIATION_STACK_API_KEY is not configured")
    return await _call(
        "aviation",
        {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(SERVER_DIR / "aviation.py")],
            "env": _stdio_env(AVIATION_STACK_API_KEY=settings.aviation_stack_api_key),
        },
        "list_airports",
        {"search": search, "limit": limit, "offset": 0},
    )


async def list_airlines(search: str = "", limit: int = 8) -> Any:
    if not settings.aviation_stack_api_key:
        raise ProviderUnavailable("AVIATION_STACK_API_KEY is not configured")
    return await _call(
        "aviation",
        {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(SERVER_DIR / "aviation.py")],
            "env": _stdio_env(AVIATION_STACK_API_KEY=settings.aviation_stack_api_key),
        },
        "list_airlines",
        {"search": search, "limit": limit, "offset": 0},
    )


async def current_weather(city: str) -> Any:
    if not settings.openweather_api_key:
        raise ProviderUnavailable("OPENWEATHER_API_KEY is not configured")
    return await _call(
        "weather",
        {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(SERVER_DIR / "weather.py")],
            "env": _stdio_env(OPENWEATHER_API_KEY=settings.openweather_api_key),
        },
        "get_current_weather",
        {"city": city},
    )


async def forecast(city: str) -> Any:
    if not settings.openweather_api_key:
        raise ProviderUnavailable("OPENWEATHER_API_KEY is not configured")
    return await _call(
        "weather",
        {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(SERVER_DIR / "weather.py")],
            "env": _stdio_env(OPENWEATHER_API_KEY=settings.openweather_api_key),
        },
        "get_forecast",
        {"city": city},
    )
