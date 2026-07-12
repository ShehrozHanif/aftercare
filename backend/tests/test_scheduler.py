"""Tests for Phase 5 — scheduled daily check-ins.

run_due_checkins is the unit the scheduler loop fires; POST /checkins/run
exposes the same function for the live demo. Must be idempotent per day.
"""

from datetime import UTC, datetime, timedelta

from app import models
from app.services import checkins as checkins_service
from tests.conftest import AHMED_ID, chat


async def test_run_starts_checkin_for_patient_without_one_today(client):
    res = await client.post("/checkins/run")
    assert res.status_code == 200
    assert res.json()["started"] == [AHMED_ID]

    convo = await client.get(f"/patients/{AHMED_ID}/conversation")
    texts = [m["text"] for m in convo.json()["messages"]]
    assert any("check-in" in t.lower() for t in texts), "greeting must be sent"


async def test_run_is_idempotent_within_a_day(client):
    first = await client.post("/checkins/run")
    assert first.json()["started"] == [AHMED_ID]
    second = await client.post("/checkins/run")
    assert second.json()["started"] == []


async def test_run_skips_patient_who_chatted_today(client):
    await chat(client, "Feeling okay, taking my medicines")
    res = await client.post("/checkins/run")
    assert res.json()["started"] == []


async def test_run_fires_for_yesterdays_conversation(client, db_sessionmaker):
    async with db_sessionmaker() as session:
        session.add(
            models.Conversation(
                patient_id=AHMED_ID,
                started_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await session.commit()
    res = await client.post("/checkins/run")
    assert res.json()["started"] == [AHMED_ID]


async def test_whatsapp_patient_gets_greeting_delivered(
    client, db_sessionmaker, monkeypatch
):
    async with db_sessionmaker() as session:
        patient = await session.get(models.Patient, AHMED_ID)
        patient.channel = "whatsapp"
        patient.phone = "+923001112233"
        await session.commit()

    sent: list[tuple[str, str]] = []

    async def fake_send(to: str, body: str):
        sent.append((to, body))
        return "SM_fake"

    monkeypatch.setattr(checkins_service, "send_whatsapp", fake_send)

    res = await client.post("/checkins/run")
    assert res.json()["started"] == [AHMED_ID]
    assert len(sent) == 1
    assert sent[0][0] == "+923001112233"
    assert "check-in" in sent[0][1].lower()


def test_seconds_until_is_always_positive_and_within_a_day():
    for hour in range(24):
        s = checkins_service._seconds_until(hour)
        assert 0 < s <= 24 * 3600
