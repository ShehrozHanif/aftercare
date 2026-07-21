"""COPD discharge checklist.

Source: standard COPD self-management / exacerbation discharge advice —
the "your COPD is getting worse if... seek urgent help if..." guidance
given after a flare-up (increasing breathlessness, more/discoloured
sputum, worsening cough/wheeze, chest infection signs).
REQUIRES CLINICIAN REVIEW before any real-world use (CLAUDE.md §2.7).
The agent never shows these labels or names a diagnosis to the patient.

Keyword discipline (CLAUDE.md §1.5): COPD patients are often somewhat
breathless and cough at baseline, so keywords are qualified ("more
breathless", "coughing more") to avoid flagging their normal state; the
signs describe a *change for the worse* from usual.
"""

from app.agent.conditions.base import ConditionChecklist, WarningSign

CHECKLIST = ConditionChecklist(
    name="copd",
    display_name="COPD",
    intro_questions=(
        "How are you feeling today, in your own words?",
        "How is your breathing compared with a normal day for you?",
        "Any change in your cough, or in the phlegm you're bringing up (more than usual, or a different colour)?",
        "Are you managing to take your medicines and inhalers as usual?",
    ),
    warning_signs=(
        # ---- URGENT: escalate immediately (nurse contacts now) ----
        WarningSign(
            id="severe_breathlessness",
            description="Severe breathlessness — breathless at rest, fighting for breath, or can't finish a sentence",
            severity="URGENT",
            keywords=(
                "can't breathe",
                "cannot breathe",
                "struggling to breathe",
                "breathless at rest",
                "gasping",
                "fighting for breath",
                "can't get my breath",
                "can't catch my breath",
                "suffocating",
            ),
        ),
        WarningSign(
            id="blue_lips",
            description="Blue lips or fingertips (possible low oxygen)",
            severity="URGENT",
            keywords=(
                "lips are blue",
                "blue lips",
                "fingers are blue",
                "turning blue",
                "going blue",
            ),
        ),
        WarningSign(
            id="confusion_drowsy",
            description="New confusion or unusual drowsiness (possible low oxygen / high CO2)",
            severity="URGENT",
            keywords=(
                "confused",
                "confusion",
                "very drowsy",
                "can't stay awake",
                "not making sense",
                "disoriented",
            ),
        ),
        WarningSign(
            id="coughing_blood",
            description="Coughing up blood",
            severity="URGENT",
            keywords=(
                "coughing up blood",
                "coughing blood",
                "blood in my phlegm",
                "blood in my mucus",
                "blood in my sputum",
            ),
        ),
        WarningSign(
            id="chest_pain",
            description="Chest pain",
            severity="URGENT",
            keywords=("chest pain", "chest hurts", "pain in my chest"),
        ),
        # ---- WARNING: flag nurse for same-day callback ----
        WarningSign(
            id="increased_breathlessness",
            description="More short of breath than usual, or breathless doing less than before",
            severity="WARNING",
            # NOTE: no bare "breathless"/"short of breath" — baseline for COPD;
            # the sign is a worsening from the patient's usual.
            keywords=(
                "more breathless",
                "more short of breath",
                "harder to breathe",
                "breathing is worse",
                "worse breathing",
                "breathing has got worse",
                "out of breath more",
                "more puffed",
                "more out of breath",
                "breathless doing",
            ),
        ),
        WarningSign(
            id="sputum_change",
            description="More phlegm than usual, or it has changed colour (yellow, green, or brown)",
            severity="WARNING",
            keywords=(
                "more phlegm",
                "more mucus",
                "more sputum",
                "more catarrh",
                "coughing up more",
                "yellow phlegm",
                "green phlegm",
                "brown phlegm",
                "yellow mucus",
                "green mucus",
                "coughing up green",
                "coughing up yellow",
                "phlegm is green",
                "phlegm is yellow",
                "darker phlegm",
                "thicker phlegm",
            ),
        ),
        WarningSign(
            id="worsening_cough",
            description="Coughing more than usual",
            severity="WARNING",
            keywords=(
                "coughing more",
                "cough is worse",
                "worse cough",
                "more coughing",
                "coughing a lot more",
                "cough has got worse",
            ),
        ),
        WarningSign(
            id="wheeze_tight_chest",
            description="More wheezing or chest tightness than usual",
            severity="WARNING",
            keywords=(
                "more wheez",
                "wheezing more",
                "wheezy",
                "chest is tight",
                "tight chest",
                "chest feels tight",
                "chest tightness",
            ),
        ),
        WarningSign(
            id="chest_infection",
            description="Fever or signs of a chest infection",
            severity="WARNING",
            keywords=(
                "fever",
                "feverish",
                "high temperature",
                "chesty cold",
                "chest infection",
                "coming down with",
                "shivering",
                "chills",
            ),
        ),
        WarningSign(
            id="medication_nonadherence",
            description="Not taking medicines or using inhalers as usual (ran out, forgot, or stopped)",
            severity="WARNING",
            negation_aware=False,  # expressed with negations by nature
            keywords=(
                "ran out",
                "stopped taking",
                "stopped my",
                "not taking my",
                "not been taking",
                "haven't taken",
                "haven't been taking",
                "forgot to take",
                "forgot my",
                "missed my",
                "out of my inhaler",
                "ran out of my inhaler",
                "not using my inhaler",
                "no inhaler",
                "side effects",
            ),
        ),
    ),
)
