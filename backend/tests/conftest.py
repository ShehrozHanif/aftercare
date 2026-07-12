"""Test fixtures: in-memory SQLite, dependency override, no API key
(forces the deterministic fallback path — tests never call the LLM)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import models
from app.config import get_settings
from app.db import Base, get_session
from app.main import app


@pytest.fixture
async def db_sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest.fixture
async def client(db_sessionmaker, monkeypatch):
    # Force deterministic fallback mode even if the dev machine has a key,
    # and blank Twilio so tests never take the live path / send messages.
    monkeypatch.setattr(get_settings(), "openai_api_key", "")
    monkeypatch.setattr(get_settings(), "twilio_account_sid", "")
    monkeypatch.setattr(get_settings(), "twilio_auth_token", "")
    monkeypatch.setattr(get_settings(), "twilio_whatsapp_from", "")

    async with db_sessionmaker() as session:
        session.add(
            models.Condition(name="heart_failure", display_name="Heart Failure")
        )
        session.add(
            models.Patient(
                name="Ahmed Raza",
                condition="heart_failure",
                channel="web",
                status="good",
            )
        )
        await session.commit()

    async def override_get_session():
        async with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


AHMED_ID = 1


async def chat(client, message: str, patient_id: int = AHMED_ID) -> dict:
    response = await client.post(
        "/chat", json={"patient_id": patient_id, "message": message}
    )
    assert response.status_code == 200, response.text
    return response.json()
