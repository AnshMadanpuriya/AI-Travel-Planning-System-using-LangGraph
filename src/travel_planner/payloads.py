"""Small, valid model payloads; original search results remain in the activity trace."""

from __future__ import annotations

import copy
import json
from typing import Any


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def byte_size(value: Any) -> int:
    return len(encode(value).encode("utf-8"))


def clip_text(text: str, budget: int) -> str:
    """Bound UTF-8 bytes without splitting a Unicode character."""
    if len(text.encode("utf-8")) <= budget:
        return text
    marker = " [earlier text shortened]"
    return text.encode("utf-8")[: max(0, budget - len(marker))].decode("utf-8", "ignore") + marker


def compact_result(value: Any, budget: int) -> Any:
    """Omit whole result rows rather than cut JSON, prices, dates, or source URLs."""
    result = copy.deepcopy(value)
    if byte_size(result) <= budget:
        return result
    if not isinstance(result, dict):
        result = {"result": result}
    result["payload_note"] = (
        "Some details were omitted to fit the request. Only use included values; "
        "unlisted dates and options are unverified. Full results are in the activity trace."
    )

    while byte_size(result) > budget:
        # Keep each option together, including its segments, exclusions and caveats.
        candidates = [
            result[key]
            for key in ("offers", "hotels", "results", "forecast", "itinerary", "result")
            if isinstance(result.get(key), list) and len(result[key]) > 1
        ]
        if not candidates:
            return {
                "error": "Result too large to summarize safely; inspect the full activity trace."
            }
        largest = max(candidates, key=byte_size)
        del largest[max(1, len(largest) // 2) :]
    return result


def compact_schema(value: Any) -> Any:
    """Remove only cosmetic schema titles, preserving validation and descriptions."""
    if isinstance(value, dict):
        return {key: compact_schema(item) for key, item in value.items() if key != "title"}
    if isinstance(value, list):
        return [compact_schema(item) for item in value]
    return value


def partial_answer(reason: str, trace: list[dict[str, Any]]) -> str:
    """Report actual tool output when the model cannot finish; never invent a plan."""
    sections = [f"### Partial travel results\n\n{reason}"]
    if not trace:
        sections.append("No travel searches completed. Please try again shortly.")

    def render(value: Any, indent: str = "") -> list[str]:
        if isinstance(value, dict):
            lines: list[str] = []
            for key, detail in value.items():
                if detail is None:
                    continue
                label = str(key).replace("_", " ").capitalize()
                if isinstance(detail, (dict, list)):
                    lines.append(f"{indent}- {label}:")
                    lines.extend(render(detail, indent + "  "))
                else:
                    lines.append(f"{indent}- {label}: {str(detail).replace(chr(10), ' ')}")
            return lines
        if isinstance(value, list):
            lines = []
            for index, detail in enumerate(value, 1):
                if isinstance(detail, (dict, list)):
                    lines.append(f"{indent}- Result {index}:")
                    lines.extend(render(detail, indent + "  "))
                else:
                    lines.append(f"{indent}- {detail}")
            return lines
        return [f"{indent}- {value}"]

    for item in trace:
        title = item["tool"].replace("_", " ").title()
        sections.append(f"#### {title} — {item['status']}")
        sections.append("\n".join(render(item["result"])))
    sections.append(
        "This is not a complete itinerary. Missing searches are unverified. "
        "Prices and availability must be checked again before booking."
    )
    return "\n\n".join(sections)
