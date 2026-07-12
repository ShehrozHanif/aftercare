"""Regression tests: repeated escalations for the same open episode must
not spam the nurse dashboard (found live: saying "I feel better" after a
red-flag report created duplicate alerts referencing the old symptoms)."""

from sqlalchemy import func, select

from app import models
from tests.conftest import AHMED_ID, chat

RED_FLAG = "my ankles are swollen and I am out of breath on the stairs"


async def _open_alerts(db_sessionmaker) -> list[tuple[int, str]]:
    async with db_sessionmaker() as session:
        rows = (
            await session.execute(
                select(models.Alert.id, models.Alert.severity).where(
                    models.Alert.patient_id == AHMED_ID,
                    models.Alert.status == "open",
                )
            )
        ).all()
    return [(r.id, r.severity) for r in rows]


async def test_same_severity_repeat_does_not_duplicate(client, db_sessionmaker):
    await chat(client, RED_FLAG)
    await chat(client, RED_FLAG)  # patient repeats the same complaint

    alerts = await _open_alerts(db_sessionmaker)
    assert len(alerts) == 1, f"expected one open alert, got {alerts}"


async def test_worsening_to_urgent_still_escalates(client, db_sessionmaker):
    await chat(client, RED_FLAG)  # WARNING
    await chat(client, "now I have chest pain")  # URGENT — genuine worsening

    alerts = await _open_alerts(db_sessionmaker)
    severities = sorted(sev for _, sev in alerts)
    assert severities == ["URGENT", "WARNING"], f"got {alerts}"


async def test_new_flag_allowed_after_acknowledgement(client, db_sessionmaker):
    await chat(client, RED_FLAG)
    (alert_id, _), = await _open_alerts(db_sessionmaker)
    res = await client.post(f"/alerts/{alert_id}/ack")
    assert res.status_code == 200

    # The episode was handled; a fresh report must flag again.
    await chat(client, RED_FLAG)
    alerts = await _open_alerts(db_sessionmaker)
    assert len(alerts) == 1
    assert alerts[0][0] != alert_id
