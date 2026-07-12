"""Centralized configuration (single config source — no scattered env reads)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM (OpenAI Agents SDK). Empty key => deterministic fallback mode.
    openai_api_key: str = ""
    llm_model: str = "gpt-5-mini"

    # Database — SQLite locally, PostgreSQL (asyncpg) on Render.
    database_url: str = "sqlite+aiosqlite:///./aftercare.db"

    # App
    frontend_url: str = "http://localhost:3000"

    # Phase 5 — scheduled daily check-ins (in-process asyncio task)
    checkin_scheduler_enabled: bool = True
    checkin_hour_utc: int = 13  # 13:00 UTC = 18:00 PKT evening check-in

    # Twilio (Phase 4 bonus — web chat never depends on these)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    # Your own WhatsApp number (e.g. +923001234567). Seeded onto Ahmed so
    # the sandbox demo maps your messages to the demo patient.
    demo_whatsapp_phone: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
