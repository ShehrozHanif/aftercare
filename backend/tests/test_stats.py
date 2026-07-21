"""Tests for GET /stats — the dashboard control-room counters."""

from tests.conftest import chat

RED_FLAG = "my ankles are swollen and I am out of breath on the stairs"


async def test_stats_initial(client):
    res = await client.get("/stats")
    assert res.status_code == 200
    body = res.json()
    assert body["patients_monitored"] == 1  # only Ahmed seeded in tests
    assert body["needs_call"] == 0
    # a check-in conversation is created lazily on first chat, so 0 so far
    assert body["checkins_today"] == 0


async def test_stats_reflect_escalation_and_checkin(client):
    await chat(client, RED_FLAG)  # creates today's conversation + an open alert

    body = (await client.get("/stats")).json()
    assert body["patients_monitored"] == 1
    assert body["needs_call"] == 1, "an open alert means the patient needs a call"
    assert body["checkins_today"] == 1, "the chat started today's check-in"
