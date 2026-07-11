"""Tests for GET /patients/{id}/checkins — the nurse-facing history."""

from datetime import UTC, datetime, timedelta

from tests.conftest import AHMED_ID, chat


async def test_checkin_history_shows_trajectory(client):
    # Day 1: all-clear conversation.
    day1 = await client.post(f"/checkins/{AHMED_ID}/start")
    assert day1.status_code == 200
    await chat(client, "Feeling okay, taking my medicines")

    # Day 4: new conversation that escalates.
    day4 = await client.post(f"/checkins/{AHMED_ID}/start")
    assert day4.status_code == 200
    await chat(client, "my ankles are swollen and I am out of breath on the stairs")

    res = await client.get(f"/patients/{AHMED_ID}/checkins")
    assert res.status_code == 200
    checkins = res.json()
    assert len(checkins) == 2

    latest, earlier = checkins  # newest first
    assert latest["escalated"] is True
    assert latest["severity"] == "WARNING"
    assert "swollen" in latest["summary"].lower() or "swelling" in latest["summary"].lower()
    assert latest["started_at"].endswith("Z")

    assert earlier["escalated"] is False
    assert earlier["severity"] is None
    assert "feeling okay" in earlier["summary"].lower()


async def test_checkin_history_unknown_patient_404(client):
    res = await client.get("/patients/999/checkins")
    assert res.status_code == 404


async def test_checkin_history_empty_for_new_patient(client):
    res = await client.get(f"/patients/{AHMED_ID}/checkins")
    assert res.status_code == 200
    assert res.json() == []


async def test_new_day_starts_new_conversation(client, db_sessionmaker):
    """A message on a new day must not be appended to yesterday's
    conversation — otherwise today's outcome is misattributed in the
    check-in history (daily check-in semantics)."""
    from app import models

    async with db_sessionmaker() as session:
        session.add(
            models.Conversation(
                patient_id=AHMED_ID,
                started_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await session.commit()

    await chat(client, "Feeling okay, taking my medicines")

    res = await client.get(f"/patients/{AHMED_ID}/checkins")
    checkins = res.json()
    assert len(checkins) == 2, "today's message must open a new conversation"
    assert "feeling okay" in checkins[0]["summary"].lower()
