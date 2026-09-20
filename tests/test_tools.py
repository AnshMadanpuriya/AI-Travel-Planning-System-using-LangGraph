from __future__ import annotations

import pytest

from mcp_server import build_budget, build_itinerary


def test_budget_math_and_split() -> None:
    result = build_budget(days=4, travelers=2, daily_budget_per_person_inr=3_000)
    assert result["on_trip_budget_inr"] == 24_000
    assert sum(result["suggested_split_inr"].values()) == 24_000


def test_budget_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="Travelers"):
        build_budget(days=4, travelers=0, daily_budget_per_person_inr=3_000)


def test_itinerary_has_requested_number_of_days() -> None:
    result = build_itinerary("Goa", 5, "beaches and food")
    assert result["destination"] == "Goa"
    assert len(result["itinerary"]) == 5
    assert result["itinerary"][0]["day"] == 1
    assert result["itinerary"][-1]["day"] == 5


def test_itinerary_rejects_excessive_length() -> None:
    with pytest.raises(ValueError, match="between 1 and 30"):
        build_itinerary("Goa", 31, "beaches")
