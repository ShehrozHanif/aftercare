"""Tests for the WhatsApp door (Phase 4) — same brain, different door.

No Twilio credentials are needed: incoming replies go back as TwiML in
the webhook response, and outbound sends no-op safely when unconfigured.
"""

from sqlalchemy import func, select

from app import models
from app.services.twilio_client import send_whatsapp

AHMED_PHONE = "+923001112233"


async def _link_phone(db_sessionmaker, patient_id: int = 1) -> None:
    async with db_sessionmaker() as session:
        patient = await session.get(models.Patient, patient_id)
        patient.phone = AHMED_PHONE
        patient.channel = "whatsapp"
        await session.commit()


async def _incoming(client, body: str, from_: str = f"whatsapp:{AHMED_PHONE}"):
    return await client.post(
        "/whatsapp/incoming", data={"From": from_, "Body": body}
    )


async def test_known_number_runs_agent_and_replies_twiml(client, db_sessionmaker):
    await _link_phone(db_sessionmaker)
    res = await _incoming(client, "Feeling okay, taking my medicines")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/xml")
    assert "<Message>" in res.text
    assert "Ahmed" in res.text  # personalized reply came from the agent


async def test_red_flag_via_whatsapp_escalates(client, db_sessionmaker):
    await _link_phone(db_sessionmaker)
    res = await _incoming(
        client, "my ankles are swollen and I am out of breath on the stairs"
    )
    assert res.status_code == 200
    # Calm reply to the patient, alarm to the nurse (§2 rule 4).
    assert "care team" in res.text.lower()
    assert "WARNING" not in res.text
    async with db_sessionmaker() as session:
        count = (
            await session.execute(select(func.count(models.Alert.id)))
        ).scalar()
        patient = await session.get(models.Patient, 1)
    assert count == 1
    assert patient.status == "alert"


async def test_unknown_number_gets_polite_pointer(client):
    res = await _incoming(client, "hello?", from_="whatsapp:+10000000000")
    assert res.status_code == 200
    assert "isn't linked" in res.text
    # No patient data leaked, no crash.


async def test_empty_body_no_crash(client, db_sessionmaker):
    await _link_phone(db_sessionmaker)
    res = await _incoming(client, "")
    assert res.status_code == 200


async def test_send_whatsapp_noop_without_credentials(monkeypatch):
    # Fallback rule (§8): unconfigured Twilio must never raise.
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "twilio_account_sid", "")
    monkeypatch.setattr(get_settings(), "twilio_auth_token", "")
    assert await send_whatsapp("+923001112233", "hi") is None


async def test_configured_mode_acks_instantly_and_replies_via_rest(
    client, db_sessionmaker, monkeypatch
):
    """Twilio abandons webhooks after ~15s (error 11200); with credentials
    configured the webhook must ack with EMPTY TwiML immediately and
    deliver the agent reply via the REST API in the background."""
    import asyncio

    from app.routers import whatsapp as whatsapp_router

    await _link_phone(db_sessionmaker)

    sent: list[tuple[str, str]] = []

    async def fake_send(to: str, body: str):
        sent.append((to, body))
        return "SM_fake"

    monkeypatch.setattr(whatsapp_router.twilio_client, "is_configured", lambda: True)
    monkeypatch.setattr(whatsapp_router.twilio_client, "send_whatsapp", fake_send)
    # Background turns must run on the test database, not the dev file DB.
    monkeypatch.setattr(whatsapp_router, "SessionLocal", db_sessionmaker)

    res = await _incoming(
        client, "my ankles are swollen and I am out of breath on the stairs"
    )
    assert res.status_code == 200
    assert "<Message>" not in res.text, "ack must be empty TwiML, reply goes via REST"

    for _ in range(50):  # wait for the background turn
        if sent:
            break
        await asyncio.sleep(0.1)
    assert sent, "background turn must deliver the reply via REST"
    assert sent[0][0] == AHMED_PHONE
    assert "care team" in sent[0][1].lower()  # calm reply (§2 rule 4)

    async with db_sessionmaker() as session:
        patient = await session.get(models.Patient, 1)
        assert patient.status == "alert"
