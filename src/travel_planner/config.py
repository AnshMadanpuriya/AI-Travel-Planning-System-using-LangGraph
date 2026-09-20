"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class Settings:
    """Runtime settings without ever exposing secret values."""

    groq_api_key: str | None
    groq_model: str
    serpapi_api_key: str | None
    tavily_api_key: str | None
    request_timeout_seconds: int
    max_agent_steps: int
    mcp_server_path: Path

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            serpapi_api_key=os.getenv("SERPAPI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            request_timeout_seconds=_positive_int("REQUEST_TIMEOUT_SECONDS", 30),
            max_agent_steps=_positive_int("MAX_AGENT_STEPS", 8),
            mcp_server_path=PROJECT_ROOT / "mcp_server.py",
        )

    def require_agent_key(self) -> None:
        if not self.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is missing. Copy .env.example to .env and add your key."
            )

    def capability_status(self) -> dict[str, bool]:
        return {
            "AI planner": bool(self.groq_api_key),
            "Live flights & hotels": bool(self.serpapi_api_key),
            "Destination research": bool(self.tavily_api_key),
            "Weather forecast": True,
        }
