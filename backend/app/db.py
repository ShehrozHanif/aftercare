"""Async SQLAlchemy engine / session layer.

MVP note: tables are created on startup via ``init_db()`` — no Alembic
migrations for the 48h hackathon build.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(get_settings().database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — one session per request."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables (idempotent)."""
    from app import models  # noqa: F401 — register mappings

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
