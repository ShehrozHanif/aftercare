"""Tests for GET /patients/{id}/report — the nurse-facing recovery report."""

from tests.conftest import AHMED_ID, chat


async def _report(client) -> dict:
    res = await client.get(f"/patients/{AHMED_ID}/report")
    assert res.status_code == 200
    return res.json()


async def test_report_empty_state(client):
    report = await _report(client)
    assert report["patient_name"] == "Ahmed Raza"
    assert report["condition_display_name"] == "Heart Failure"
    assert report["checkins_sent"] == 0
    assert report["checkins_answered"] == 0
    assert report["alerts_total"] == 0
    assert report["symptom_mentions"] == []
    assert report["generated_at"].endswith("Z")


async def test_report_aggregates_recovery_trajectory(client):
    # An answered all-clear check-in, then an escalating one.
    await client.post(f"/checkins/{AHMED_ID}/start")
    await chat(client, "Feeling okay, taking my medicines")
    await chat(client, "my ankles are swollen and I am out of breath on the stairs")

    report = await _report(client)
    assert report["checkins_sent"] == 1  # same day -> one conversation
    assert report["checkins_answered"] == 1
    assert report["alerts_total"] == 1
    assert report["alerts_open"] == 1
    assert report["medication_concerns"] == 0
    mention = report["symptom_mentions"][0]
    assert mention["severity"] == "WARNING"
    assert any("swelling" in s.lower() for s in mention["signs"])


async def test_report_counts_medication_concerns(client):
    await chat(client, "I stopped taking my medicines, they make me dizzy")
    report = await _report(client)
    assert report["medication_concerns"] == 1


async def test_report_counts_unanswered_checkins(client):
    await client.post(f"/checkins/{AHMED_ID}/start")  # greeting, no reply
    report = await _report(client)
    assert report["checkins_sent"] == 1
    assert report["checkins_answered"] == 0


async def test_report_unknown_patient_404(client):
    res = await client.get("/patients/999/report")
    assert res.status_code == 404
