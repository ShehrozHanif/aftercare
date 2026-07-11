"""Core safety tests: red flags escalate, all-clear does not, and the
patient-facing reply stays calm and non-diagnostic (CLAUDE.md §2)."""

from tests.conftest import AHMED_ID, chat

ALARMING_FRAGMENTS = (
    "urgent",
    "warning",
    "emergency",
    "alarm",
    "red flag",
    "heart failure",
    "diagnos",
    "911",
)


def assert_calm_and_non_diagnostic(reply: str) -> None:
    lowered = reply.lower()
    for fragment in ALARMING_FRAGMENTS:
        assert fragment not in lowered, f"Alarming/diagnostic reply: {reply!r}"


async def _patient_status(client, patient_id: int = AHMED_ID) -> str:
    patients = (await client.get("/patients")).json()
    return next(p for p in patients if p["id"] == patient_id)["status"]


async def test_red_flag_creates_warning_alert(client):
    data = await chat(
        client, "my ankles are swollen and I get out of breath on the stairs"
    )
    alert = data["alert"]
    assert alert is not None
    assert alert["severity"] == "WARNING"
    assert alert["status"] == "open"
    assert alert["patient_id"] == AHMED_ID
    assert alert["matched_signs"]  # the swelling / breathlessness signs

    # Patient-facing reply: calm, reassuring, mentions the care team,
    # never the alarm or a diagnosis.
    assert "care team" in data["reply"].lower()
    assert_calm_and_non_diagnostic(data["reply"])

    assert await _patient_status(client) == "alert"


async def test_all_clear_creates_no_alert(client):
    data = await chat(
        client,
        "I feel good today, no new swelling, and I'm taking my medicines",
    )
    assert data["alert"] is None
    assert data["reply"]
    assert await _patient_status(client) == "good"


async def test_urgent_chest_pain(client):
    data = await chat(client, "I have chest pain and I feel dizzy")
    alert = data["alert"]
    assert alert is not None
    assert alert["severity"] == "URGENT"
    # Even on URGENT the patient-facing reply stays calm.
    assert_calm_and_non_diagnostic(data["reply"])
    assert await _patient_status(client) == "alert"


async def test_medication_nonadherence_warns(client):
    data = await chat(client, "I ran out of my tablets two days ago")
    alert = data["alert"]
    assert alert is not None
    assert alert["severity"] == "WARNING"


async def test_denied_symptoms_do_not_escalate(client):
    data = await chat(client, "No swelling and I am not short of breath")
    assert data["alert"] is None
