"""Heart Failure discharge checklist (the fully built demo condition).

Source: standard heart-failure discharge warning-sign guidance — the
"call your doctor / call 911 if..." instructions hospitals give HF
patients (CLAUDE.md §7). REQUIRES CLINICIAN REVIEW before any
real-world use. The agent never shows these labels to the patient.
"""

from app.agent.conditions.base import ConditionChecklist, WarningSign

CHECKLIST = ConditionChecklist(
    name="heart_failure",
    display_name="Heart Failure",
    intro_questions=(
        "How are you feeling today, in your own words?",
        "Have you noticed any new swelling in your legs, ankles, feet, or tummy?",
        "How is your breathing — any more breathless than usual, for example on stairs or when lying flat?",
        "Are you managing to take your medicines as usual?",
    ),
    warning_signs=(
        # ---- URGENT: escalate immediately (nurse contacts now) ----
        WarningSign(
            id="chest_pain",
            description="Chest pain or pressure",
            severity="URGENT",
            keywords=(
                "chest pain",
                "chest pressure",
                "pressure in my chest",
                "pain in my chest",
                "chest hurts",
                "chest feels tight",
                "tightness in my chest",
            ),
        ),
        WarningSign(
            id="severe_breathlessness",
            description="Severe or sudden shortness of breath / breathless at rest",
            severity="URGENT",
            keywords=(
                "breathless at rest",
                "short of breath at rest",
                "can't breathe",
                "cannot breathe",
                "struggling to breathe",
                "hard to breathe",
                "gasping",
                "severe shortness of breath",
                "suffocating",
            ),
        ),
        WarningSign(
            id="fainting",
            description="Fainting or near-fainting",
            severity="URGENT",
            keywords=("faint", "passed out", "blacked out", "collapsed"),
        ),
        WarningSign(
            id="rapid_irregular_heartbeat",
            description="Very fast or irregular heartbeat with dizziness",
            severity="URGENT",
            keywords=(
                "heart is racing",
                "heart racing",
                "racing heart",
                "irregular heartbeat",
                "heart is pounding",
                "pounding heart",
                "palpitations",
                "skipping beats",
            ),
        ),
        WarningSign(
            id="new_confusion",
            description="New confusion",
            severity="URGENT",
            keywords=("confused", "confusion", "disoriented", "can't think straight"),
        ),
        # ---- WARNING: flag nurse for same-day callback ----
        WarningSign(
            id="swelling",
            description="New or increased swelling in legs, ankles, feet, or abdomen",
            severity="WARNING",
            keywords=(
                "swollen",
                "swelling",
                "puffy",
                "ankles are bigger",
                "legs are bigger",
                "shoes feel tight",
                "tighter shoes",
            ),
        ),
        WarningSign(
            id="weight_gain",
            description="Sudden weight gain (~1-1.5 kg in a day or ~2.3 kg in a week)",
            severity="WARNING",
            keywords=("gained", "weight gain", "weight went up", "put on weight", "heavier"),
        ),
        WarningSign(
            id="exertional_breathlessness",
            description="Increasing shortness of breath on exertion, or breathless lying flat / needing more pillows",
            severity="WARNING",
            keywords=(
                "out of breath",
                "short of breath",
                "shortness of breath",
                "breathless",
                "catch my breath",
                "winded",
                "more pillows",
                "breathe lying down",
                "puffing",
            ),
        ),
        WarningSign(
            id="cough_wheeze",
            description="New or worsening cough or wheezing",
            severity="WARNING",
            keywords=("cough", "wheez"),
        ),
        WarningSign(
            id="fatigue",
            description="Increasing fatigue / can't do usual activities",
            severity="WARNING",
            # NOTE: deliberately no bare "tired" — mild tiredness is normal
            # in early recovery (see jounry.md Day-1 script); the sign is
            # *increasing* fatigue that limits usual activities.
            keywords=(
                "more tired",
                "so tired",
                "very tired",
                "too tired",
                "exhausted",
                "fatigue",
                "no energy",
                "worn out",
                "can't do my usual",
            ),
        ),
        WarningSign(
            id="medication_nonadherence",
            description="Not taking medication (ran out, forgot, or stopped due to side effects)",
            severity="WARNING",
            negation_aware=False,  # expressed with negations by nature
            keywords=(
                "ran out",
                "stopped taking",
                "stopped my",
                "not taking my med",
                "not been taking",
                "haven't taken",
                "haven't been taking",
                "forgot to take",
                "forgot my",
                "missed my",
                "missed a dose",
                "missed doses",
                "skipped my",
                "side effects",
            ),
        ),
    ),
)
