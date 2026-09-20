"""Compatibility wrapper around the MCP server's normalized flight search."""

from mcp_server import search_flights_data


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    max_price_inr: int = 0,
):
    return search_flights_data(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        adults=adults,
        max_price_inr=max_price_inr,
    )
