"""Tests for POST /patients/{id}/resolve — the nurse closing a case.

Lifecycle: escalation (red) -> acknowledge (watch) -> resolve (good).
The agent can only raise concern; only a human lowers it (§2.2).
"""

from sqlalchemy import select

from app import models
from tests.conftest import AHMED_ID, chat

RED_FLAG = "my ankles are swollen and I am out of breath on the stairs"


async def _ack_open_alert(client) -> int:
    patients = (await client.get("/patients")).json()
    alert_id = patients[0]["open_alerts"][0]["id"]
    res = await client.post(f"/alerts/{alert_id}/ack")
    assert res.status_code == 200
    return alert_id


async def test_resolve_closes_the_case(client, db_sessionmaker):
    await chat(client, RED_FLAG)
    await _ack_open_alert(client)

    res = await client.post(f"/patients/{AHMED_ID}/resolve")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "good"
    assert body["open_alerts"] == []

    async with db_sessionmaker() as session:
        statuses = (
            (
                await session.execute(
                    select(models.Alert.status).where(
                        models.Alert.patient_id == AHMED_ID
                    )
                )
            )
            .scalars()
            .all()
        )
    assert statuses == ["resolved"], "acknowledged alerts must become resolved"


async def test_resolve_refused_while_alert_open(client):
    await chat(client, RED_FLAG)
    res = await client.post(f"/patients/{AHMED_ID}/resolve")
    assert res.status_code == 409


async def test_resolve_unknown_patient_404(client):
    res = await client.post("/patients/999/resolve")
    assert res.status_code == 404


async def test_fresh_report_after_resolve_escalates_again(client, db_sessionmaker):
    await chat(client, RED_FLAG)
    await _ack_open_alert(client)
    await client.post(f"/patients/{AHMED_ID}/resolve")

    await chat(client, RED_FLAG)  # new episode after case closed

    async with db_sessionmaker() as session:
        patient = await session.get(models.Patient, AHMED_ID)
        open_count = len(
            (
                await session.execute(
                    select(models.Alert).where(
                        models.Alert.patient_id == AHMED_ID,
                        models.Alert.status == "open",
                    )
                )
            )
            .scalars()
            .all()
        )
    assert patient.status == "alert"
    assert open_count == 1
