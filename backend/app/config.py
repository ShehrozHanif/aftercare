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

    # Twilio (Phase 4 bonus — unused in core flow)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
