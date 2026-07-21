"""Regression tests for the deterministic sign matcher.

These phrases gate the stage demo: the Day-1 all-clear script must stay
green (no false alarms via the safety net), and the red-flag phrases must
always escalate. See jounry.md for the scripted conversations.
"""

import pytest

from app.agent.conditions import get_checklist, match_signs

HF = get_checklist("heart_failure")
POST = get_checklist("post_surgical")
COPD = get_checklist("copd")


@pytest.mark.parametrize(
    "text",
    [
        # Day-1 all-clear script (jounry.md) — mild tiredness is normal.
        "Okay I think. A bit tired.",
        "feeling a bit tired but otherwise good",
        "not really breathless, just tired from the walk",
        # Denials must not match their own symptom keywords.
        "No swelling, no trouble breathing",
        "No, not more tired than usual",
        "slept fine, no new swelling in my legs",
        "I am fine, taking my medicines",
        # Chip answers carry no symptom context.
        "Yes",
        "No",
        "A little",
    ],
)
def test_all_clear_phrases_stay_ok(text):
    severity, signs = match_signs(HF, text)
    assert severity == "OK", f"false alarm on {text!r}: {[s.id for s in signs]}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # The Day-4 demo trigger (CLAUDE.md §7).
        ("my ankles are swollen and I am out of breath on the stairs", "WARNING"),
        ("much more tired than yesterday", "WARNING"),
        # "cannot/can't do things" is an affirmation, never a denial.
        ("I am so tired I cannot do my shopping anymore", "WARNING"),
        ("I stopped taking my medicines, they make me dizzy", "WARNING"),
        ("I cannot breathe properly even sitting down", "URGENT"),
        ("chest pain", "URGENT"),
    ],
)
def test_red_flag_phrases_escalate(text, expected):
    severity, _ = match_signs(HF, text)
    assert severity == expected


# --- Post-surgical recovery ------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # Fatima's seeded all-clear line (seed.py) — soreness is normal post-op.
        "The wound is a little sore but I'm okay",
        "feeling okay, the wound is a bit sore but healing well",
        "no fever, no redness around the wound",
        "some bruising but it's getting better",
        "Yes",
        "No",
    ],
)
def test_post_surgical_all_clear_stays_ok(text):
    severity, signs = match_signs(POST, text)
    assert severity == "OK", f"false alarm on {text!r}: {[s.id for s in signs]}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # The one-tap demo chip (patient/page.tsx SUGGESTED_BY_CONDITION).
        ("My wound is red and oozing and I've had a fever since last night", "WARNING"),
        ("the skin around the wound is red and warm", "WARNING"),
        ("my pain is getting worse, not better", "WARNING"),
        ("the wound has opened up", "URGENT"),
        ("it won't stop bleeding", "URGENT"),
        ("I stopped taking my antibiotics", "WARNING"),
    ],
)
def test_post_surgical_red_flags_escalate(text, expected):
    severity, _ = match_signs(POST, text)
    assert severity == expected


# --- COPD ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # Baseline COPD state must not flag — mild breathlessness/cough is usual.
        "breathing feels steady today, about the same as usual",
        "a bit breathless as always but no worse than usual",
        "no change in my cough or phlegm",
        "Yes",
        "No",
    ],
)
def test_copd_all_clear_stays_ok(text):
    severity, signs = match_signs(COPD, text)
    assert severity == "OK", f"false alarm on {text!r}: {[s.id for s in signs]}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # The one-tap demo chip (patient/page.tsx SUGGESTED_BY_CONDITION).
        ("I'm much more breathless than usual and coughing up green phlegm", "WARNING"),
        ("my breathing is worse and I have more phlegm", "WARNING"),
        ("coughing more than usual with a fever", "WARNING"),
        ("I can't catch my breath even sitting still", "URGENT"),
        ("my lips are blue", "URGENT"),
        ("I ran out of my inhaler", "WARNING"),
    ],
)
def test_copd_red_flags_escalate(text, expected):
    severity, _ = match_signs(COPD, text)
    assert severity == expected
