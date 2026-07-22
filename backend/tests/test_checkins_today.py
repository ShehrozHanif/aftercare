"""Tests for GET /checkins/today — the clickable 'Check-ins today' worklist."""

from tests.conftest import AHMED_ID, chat

RED_FLAG = "my ankles are swollen and I am out of breath on the stairs"
ALL_CLEAR = "I feel good today, no swelling and breathing is fine"


async def test_checkins_today_empty_before_any_chat(client):
    res = await client.get("/checkins/today")
    assert res.status_code == 200
    assert res.json() == []  # no conversation started yet


async def test_checkin_appears_after_chat_with_patient_detail(client):
    await chat(client, ALL_CLEAR)  # starts today's conversation + a patient reply

    body = (await client.get("/checkins/today")).json()
    assert len(body) == 1
    item = body[0]
    assert item["patient_id"] == AHMED_ID
    assert item["patient_name"] == "Ahmed Raza"
    assert item["condition_display_name"] == "Heart Failure"
    assert item["answered"] is True  # the patient sent a message
    assert item["escalated"] is False
    assert item["severity"] is None


async def test_escalated_checkin_carries_severity(client):
    await chat(client, RED_FLAG)

    body = (await client.get("/checkins/today")).json()
    assert len(body) == 1
    item = body[0]
    assert item["answered"] is True
    assert item["escalated"] is True
    assert item["severity"] in {"WARNING", "URGENT"}
