from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
    aviation_stack_api_key: str | None = (
        os.getenv("AVIATION_STACK_API_KEY") or os.getenv("AVIATIONSTACK_API_KEY")
    )
    openweather_api_key: str | None = os.getenv("OPENWEATHER_API_KEY")
    database_url: str | None = os.getenv("DATABASE_URL")
    demo_mode: bool = os.getenv("TRAVEL_AGENT_DEMO_MODE", "false").lower() == "true"


settings = Settings()


def get_llm():
    if settings.demo_mode or not settings.groq_api_key:
        return None

    from langchain_groq import ChatGroq

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.2,
    )
