"""Route-level tests: patients list, transcript, check-in start, ack."""

from tests.conftest import AHMED_ID, chat


async def test_patients_list(client):
    response = await client.get("/patients")
    assert response.status_code == 200
    patients = response.json()
    ahmed = next(p for p in patients if p["id"] == AHMED_ID)
    assert ahmed["name"] == "Ahmed Raza"
    assert ahmed["condition"] == "heart_failure"
    assert ahmed["condition_display_name"] == "Heart Failure"
    assert ahmed["status"] == "good"
    assert ahmed["open_alerts"] == []


async def test_open_alert_appears_on_patient_list(client):
    await chat(client, "my ankles are swollen and I get out of breath on the stairs")
    patients = (await client.get("/patients")).json()
    ahmed = next(p for p in patients if p["id"] == AHMED_ID)
    assert ahmed["status"] == "alert"
    assert len(ahmed["open_alerts"]) == 1
    assert ahmed["open_alerts"][0]["severity"] == "WARNING"


async def test_checkin_start_sends_greeting(client):
    response = await client.post(f"/checkins/{AHMED_ID}/start")
    assert response.status_code == 200
    data = response.json()
    assert "Ahmed" in data["reply"]
    assert data["conversation_id"] > 0


async def test_conversation_transcript(client):
    await client.post(f"/checkins/{AHMED_ID}/start")
    await chat(client, "Feeling okay today, thanks")

    response = await client.get(f"/patients/{AHMED_ID}/conversation")
    assert response.status_code == 200
    transcript = response.json()
    assert transcript["patient_id"] == AHMED_ID
    senders = [m["sender"] for m in transcript["messages"]]
    assert senders == ["agent", "patient", "agent"]  # greeting, reply, close
    assert transcript["messages"][1]["text"] == "Feeling okay today, thanks"


async def test_ack_alert(client):
    data = await chat(client, "I have chest pain")
    alert_id = data["alert"]["id"]

    response = await client.post(f"/alerts/{alert_id}/ack")
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"

    # Patient drops from 'alert' to 'watch' once the only open alert is acked.
    patients = (await client.get("/patients")).json()
    ahmed = next(p for p in patients if p["id"] == AHMED_ID)
    assert ahmed["status"] == "watch"
    assert ahmed["open_alerts"] == []


async def test_chat_unknown_patient_404(client):
    response = await client.post(
        "/chat", json={"patient_id": 999, "message": "hello"}
    )
    assert response.status_code == 404


async def test_chat_empty_message_rejected(client):
    response = await client.post("/chat", json={"patient_id": AHMED_ID, "message": ""})
    assert response.status_code == 422
