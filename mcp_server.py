"""FastMCP server exposing grounded travel-planning tools."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from typing import Any

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("VoyageGraph Travel Tools")
SERPAPI_URL = "https://serpapi.com/search.json"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TAVILY_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT = max(int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")), 5)
_location_cache: dict[str, dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _parse_date(value: str, field_name: str, *, allow_past: bool = False) -> date:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from exc
    if not allow_past and parsed < date.today():
        raise ValueError(f"{field_name} cannot be in the past.")
    return parsed


def _safe_error(service: str, error: Exception) -> dict[str, str]:
    if isinstance(error, requests.HTTPError) and error.response is not None:
        return {"error": f"{service} returned HTTP {error.response.status_code}."}
    if isinstance(error, ValueError):
        return {"error": str(error)}
    if isinstance(error, requests.RequestException):
        return {"error": f"{service} could not be reached. Please try again."}
    return {"error": f"{service} failed unexpectedly."}


def _get_json(url: str, *, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _serpapi_request(parameters: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError(
            "SERPAPI_API_KEY is not configured, so live flight or hotel data is unavailable."
        )
    data = _get_json(SERPAPI_URL, params={**parameters, "api_key": api_key})
    if data.get("error"):
        raise ValueError(str(data["error"]))
    return data


def _resolve_flight_location(place: str) -> dict[str, Any]:
    clean_place = place.strip()
    if not clean_place:
        raise ValueError("Flight location cannot be empty.")

    cache_key = clean_place.casefold()
    if cache_key in _location_cache:
        return _location_cache[cache_key]

    if len(clean_place) == 3 and clean_place.isalpha() and clean_place.isupper():
        resolved = {
            "name": clean_place,
            "search_id": clean_place,
            "airports": [{"code": clean_place, "name": "Provided IATA airport code"}],
        }
        _location_cache[cache_key] = resolved
        return resolved

    data = _serpapi_request(
        {
            "engine": "google_flights_autocomplete",
            "q": clean_place,
            "gl": "in",
            "hl": "en",
            "exclude_regions": "true",
        }
    )
    suggestions = data.get("suggestions", [])
    if not suggestions:
        raise ValueError(f"No airport or city match was found for '{clean_place}'.")

    suggestion = suggestions[0]
    resolved = {
        "name": suggestion.get("name", clean_place),
        "description": suggestion.get("description"),
        "search_id": suggestion.get("id"),
        "airports": [
            {
                "code": airport.get("id"),
                "name": airport.get("name"),
                "city": airport.get("city"),
            }
            for airport in suggestion.get("airports", [])
        ],
    }
    if not resolved["search_id"]:
        raise ValueError(f"No flight search identifier was found for '{clean_place}'.")
    _location_cache[cache_key] = resolved
    return resolved


def build_itinerary(destination: str, days: int, interests: str) -> dict[str, Any]:
    """Pure itinerary skeleton used by the MCP tool and unit tests."""

    if not destination.strip():
        raise ValueError("Destination cannot be empty.")
    if days < 1 or days > 30:
        raise ValueError("Days must be between 1 and 30.")

    plans: list[dict[str, Any]] = []
    for day_number in range(1, days + 1):
        if day_number == 1:
            theme = "Arrival and orientation"
            morning = "Arrive, transfer, and check in"
            afternoon = f"Explore a low-effort neighbourhood in {destination}"
            evening = "Try nearby local food and rest"
        elif day_number == days:
            theme = "Flexible final day and departure"
            morning = "Use buffer time for a nearby attraction or shopping"
            afternoon = "Check out and prepare for the return journey"
            evening = "Departure"
        else:
            theme = f"{interests} discovery"
            morning = f"One major {interests} experience"
            afternoon = "A nearby attraction with realistic travel time"
            evening = "Local culture, food, or a relaxed walk"
        plans.append(
            {
                "day": day_number,
                "theme": theme,
                "morning": morning,
                "afternoon": afternoon,
                "evening": evening,
            }
        )

    return {
        "destination": destination,
        "days": days,
        "interests": interests,
        "itinerary": plans,
        "verification_note": (
            "This is a planning skeleton. Verify attraction hours, tickets, travel time, and closures."
        ),
    }


def build_budget(days: int, travelers: int, daily_budget_per_person_inr: int) -> dict[str, Any]:
    """Pure budget estimate used by the MCP tool and unit tests."""

    if days < 1 or days > 30:
        raise ValueError("Days must be between 1 and 30.")
    if travelers < 1 or travelers > 20:
        raise ValueError("Travelers must be between 1 and 20.")
    if daily_budget_per_person_inr < 1:
        raise ValueError("Daily budget per person must be positive.")

    on_trip_budget = days * travelers * daily_budget_per_person_inr
    return {
        "days": days,
        "travelers": travelers,
        "daily_budget_per_person_inr": daily_budget_per_person_inr,
        "on_trip_budget_inr": on_trip_budget,
        "suggested_split_inr": {
            "stay": round(on_trip_budget * 0.45),
            "food": round(on_trip_budget * 0.25),
            "local_transport": round(on_trip_budget * 0.15),
            "activities_and_buffer": round(on_trip_budget * 0.15),
        },
        "excludes": [
            "intercity flights or trains",
            "visa and insurance",
            "shopping",
        ],
        "note": "This is a planning estimate, not a quoted price.",
    }


def search_flights_data(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    max_price_inr: int = 0,
) -> dict[str, Any]:
    """Fetch a normalized one-way Google Flights snapshot through SerpApi."""

    try:
        if not origin.strip() or not destination.strip():
            raise ValueError("Origin and destination are required.")
        _parse_date(departure_date, "departure_date")
        if adults < 1 or adults > 9:
            raise ValueError("Adults must be between 1 and 9.")
        if max_price_inr < 0:
            raise ValueError("Maximum flight price cannot be negative.")

        origin_location = _resolve_flight_location(origin)
        destination_location = _resolve_flight_location(destination)
        if origin_location["search_id"] == destination_location["search_id"]:
            raise ValueError("Origin and destination must be different.")

        parameters: dict[str, Any] = {
            "engine": "google_flights",
            "departure_id": origin_location["search_id"],
            "arrival_id": destination_location["search_id"],
            "outbound_date": departure_date,
            "type": "2",
            "travel_class": "1",
            "adults": adults,
            "currency": "INR",
            "gl": "in",
            "hl": "en",
            "sort_by": "2",
            "deep_search": "false",
        }
        if max_price_inr:
            parameters["max_price"] = max_price_inr

        data = _serpapi_request(parameters)
        raw_offers = data.get("best_flights", []) + data.get("other_flights", [])
        offers: list[dict[str, Any]] = []
        for raw_offer in raw_offers[:5]:
            segments = raw_offer.get("flights", [])
            if not segments:
                continue
            first, last = segments[0], segments[-1]
            offers.append(
                {
                    "airlines": list(
                        dict.fromkeys(
                            segment.get("airline") for segment in segments if segment.get("airline")
                        )
                    ),
                    "flight_numbers": [
                        segment.get("flight_number")
                        for segment in segments
                        if segment.get("flight_number")
                    ],
                    "departure": first.get("departure_airport"),
                    "arrival": last.get("arrival_airport"),
                    "stops": max(len(segments) - 1, 0),
                    "layovers": raw_offer.get("layovers", []),
                    "duration_minutes": raw_offer.get("total_duration"),
                    "price_inr": raw_offer.get("price"),
                    "emissions_grams": (raw_offer.get("carbon_emissions") or {}).get("this_flight"),
                }
            )

        return {
            "source": "Google Flights via SerpApi",
            "data_type": "live_search_snapshot",
            "checked_at_utc": data.get("search_metadata", {}).get("processed_at", _utc_now()),
            "origin": origin_location,
            "destination": destination_location,
            "departure_date": departure_date,
            "adults": adults,
            "currency": "INR",
            "offers": offers,
            "message": None if offers else "No flight options were returned for this search.",
            "verification_note": (
                "Verify final fare, taxes, baggage, passenger price scope, and seat availability "
                "on the airline or booking page."
            ),
        }
    except Exception as error:
        return _safe_error("Flight search", error)


def search_hotels_data(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    max_price_per_night_inr: int = 0,
) -> dict[str, Any]:
    """Fetch a normalized Google Hotels snapshot through SerpApi."""

    try:
        if not destination.strip():
            raise ValueError("Destination is required.")
        check_in = _parse_date(check_in_date, "check_in_date")
        check_out = _parse_date(check_out_date, "check_out_date")
        if check_out <= check_in:
            raise ValueError("check_out_date must be after check_in_date.")
        if adults < 1 or adults > 9:
            raise ValueError("Adults must be between 1 and 9.")
        if max_price_per_night_inr < 0:
            raise ValueError("Maximum nightly price cannot be negative.")

        parameters: dict[str, Any] = {
            "engine": "google_hotels",
            "q": f"Hotels in {destination}",
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "currency": "INR",
            "gl": "in",
            "hl": "en",
            "sort_by": "8",
        }
        if max_price_per_night_inr:
            parameters["max_price"] = max_price_per_night_inr

        data = _serpapi_request(parameters)
        hotels: list[dict[str, Any]] = []
        for property_data in data.get("properties", [])[:5]:
            nightly_rate = property_data.get("rate_per_night") or {}
            total_rate = property_data.get("total_rate") or {}
            hotels.append(
                {
                    "name": property_data.get("name"),
                    "type": property_data.get("type"),
                    "hotel_class": property_data.get("hotel_class"),
                    "rating": property_data.get("overall_rating"),
                    "reviews": property_data.get("reviews"),
                    "nightly_rate": nightly_rate.get("lowest"),
                    "nightly_rate_value": nightly_rate.get("extracted_lowest"),
                    "total_rate": total_rate.get("lowest"),
                    "total_rate_value": total_rate.get("extracted_lowest"),
                    "free_cancellation": property_data.get("free_cancellation"),
                    "amenities": (property_data.get("amenities") or [])[:8],
                }
            )

        return {
            "source": "Google Hotels via SerpApi",
            "data_type": "live_search_snapshot",
            "checked_at_utc": data.get("search_metadata", {}).get("processed_at", _utc_now()),
            "destination": destination,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "currency": "INR",
            "hotels": hotels,
            "message": None if hotels else "No hotels were returned for this search.",
            "verification_note": (
                "Verify room type, taxes, cancellation rules, and final availability before booking."
            ),
        }
    except Exception as error:
        return _safe_error("Hotel search", error)


def search_guides_data(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search current travel guidance using Tavily when configured."""

    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY is not configured, so live destination research is unavailable."
            )
        if not query.strip():
            raise ValueError("Search query cannot be empty.")
        response = requests.post(
            TAVILY_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": min(max(max_results, 1), 8),
                "include_answer": False,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "source": "Tavily web search",
            "checked_at_utc": _utc_now(),
            "query": query,
            "results": [
                {
                    "title": result.get("title"),
                    "url": result.get("url"),
                    "snippet": (result.get("content") or "")[:500],
                }
                for result in data.get("results", [])
            ],
            "verification_note": "Open the cited source before relying on time-sensitive guidance.",
        }
    except Exception as error:
        return _safe_error("Destination research", error)


@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    max_price_inr: int = 0,
) -> dict[str, Any]:
    """Search live one-way flight options for exact cities and a YYYY-MM-DD departure date."""

    return search_flights_data(origin, destination, departure_date, adults, max_price_inr)


@mcp.tool()
def search_hotels(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    max_price_per_night_inr: int = 0,
) -> dict[str, Any]:
    """Search live hotels for exact YYYY-MM-DD check-in and check-out dates."""

    return search_hotels_data(
        destination, check_in_date, check_out_date, adults, max_price_per_night_inr
    )


@mcp.tool()
def get_weather_forecast(
    city: str,
    start_date: str = "",
    end_date: str = "",
) -> dict[str, Any]:
    """Get current conditions and up to 16 days of weather forecasts from Open-Meteo."""

    try:
        if not city.strip():
            raise ValueError("City cannot be empty.")
        requested_range: tuple[str, str] | None = None
        if start_date or end_date:
            if not (start_date and end_date):
                raise ValueError("Provide both start_date and end_date, or leave both empty.")
            start = _parse_date(start_date, "start_date")
            end = _parse_date(end_date, "end_date")
            if end < start:
                raise ValueError("end_date must be on or after start_date.")
            if (start - date.today()).days > 15 or (end - date.today()).days > 15:
                raise ValueError(
                    "The requested trip dates are outside the available 16-day weather forecast."
                )
            requested_range = (start_date, end_date)

        geocoding = _get_json(
            OPEN_METEO_GEOCODING_URL,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
        locations = geocoding.get("results", [])
        if not locations:
            raise ValueError(f"No weather location was found for '{city}'.")
        location = locations[0]

        params: dict[str, Any] = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            ),
            "timezone": "auto",
            "forecast_days": 16,
        }
        if requested_range:
            params.update({"start_date": requested_range[0], "end_date": requested_range[1]})

        data = _get_json(OPEN_METEO_FORECAST_URL, params=params)
        daily = data.get("daily", {})
        forecast = [
            {
                "date": forecast_date,
                "weather_code": daily.get("weather_code", [None] * len(daily.get("time", [])))[i],
                "min_c": daily.get("temperature_2m_min", [None] * len(daily.get("time", [])))[i],
                "max_c": daily.get("temperature_2m_max", [None] * len(daily.get("time", [])))[i],
                "precipitation_probability_percent": daily.get(
                    "precipitation_probability_max", [None] * len(daily.get("time", []))
                )[i],
            }
            for i, forecast_date in enumerate(daily.get("time", []))
        ]
        return {
            "source": "Open-Meteo",
            "checked_at_utc": _utc_now(),
            "location": {
                "name": location.get("name"),
                "country": location.get("country"),
                "timezone": data.get("timezone"),
            },
            "current": data.get("current", {}),
            "forecast": forecast,
            "note": "Forecasts outside Open-Meteo's returned horizon are unavailable.",
        }
    except Exception as error:
        return _safe_error("Weather service", error)


@mcp.tool()
def search_destination_guides(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search current attractions, travel advice, entry rules, or local guidance with citations."""

    return search_guides_data(query, max_results)


@mcp.tool()
def create_itinerary(
    destination: str,
    days: int,
    interests: str = "sightseeing and local food",
) -> dict[str, Any]:
    """Create a realistic day-by-day planning skeleton for a destination."""

    try:
        return build_itinerary(destination, days, interests)
    except Exception as error:
        return _safe_error("Itinerary builder", error)


@mcp.tool()
def calculate_trip_budget(
    days: int,
    travelers: int,
    daily_budget_per_person_inr: int,
) -> dict[str, Any]:
    """Calculate a transparent on-trip INR budget estimate excluding intercity transport."""

    try:
        return build_budget(days, travelers, daily_budget_per_person_inr)
    except Exception as error:
        return _safe_error("Budget calculator", error)


if __name__ == "__main__":
    mcp.run()
