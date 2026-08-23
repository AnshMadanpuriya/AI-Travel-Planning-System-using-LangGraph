from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Travel Weather")


def _key() -> str:
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        raise ValueError("OPENWEATHER_API_KEY is not configured")
    return key


def _request(path: str, city: str) -> dict:
    response = httpx.get(
        f"https://api.openweathermap.org/data/2.5/{path}",
        params={"q": city, "appid": _key(), "units": "metric"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_current_weather(city: str) -> dict:
    """Return current metric weather for one city."""
    data = _request("weather", city)
    return {
        "city": data.get("name", city),
        "temperature_c": data["main"]["temp"],
        "feels_like_c": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "condition": data["weather"][0]["description"],
        "wind_speed_mps": data["wind"]["speed"],
    }


@mcp.tool()
def get_forecast(city: str) -> dict:
    """Return the next eight three-hour forecast entries for one city."""
    data = _request("forecast", city)
    rows = [
        {
            "datetime": item["dt_txt"],
            "temperature_c": item["main"]["temp"],
            "condition": item["weather"][0]["description"],
        }
        for item in data.get("list", [])[:8]
    ]
    return {"city": city, "forecast": rows}


if __name__ == "__main__":
    mcp.run()
