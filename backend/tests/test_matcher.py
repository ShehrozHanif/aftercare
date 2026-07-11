"""Regression tests for the deterministic sign matcher.

These phrases gate the stage demo: the Day-1 all-clear script must stay
green (no false alarms via the safety net), and the red-flag phrases must
always escalate. See jounry.md for the scripted conversations.
"""

import pytest

from app.agent.conditions import get_checklist, match_signs

HF = get_checklist("heart_failure")


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
