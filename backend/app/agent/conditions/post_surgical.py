"""Post-surgical recovery discharge checklist.

Source: standard post-operative discharge advice — the "call your surgeon
/ seek urgent help if..." guidance hospitals give after an operation
(wound infection, bleeding, wound breakdown, clot warning signs).
REQUIRES CLINICIAN REVIEW before any real-world use (CLAUDE.md §2.7).
The agent never shows these labels or names a diagnosis to the patient.

Keyword discipline (CLAUDE.md §1.5): the deterministic safety net runs on
every turn, so keywords are qualified to avoid matching normal recovery
("a little sore", "some bruising") — mild soreness is expected post-op;
the signs describe infection, bleeding, or worsening.
"""

from app.agent.conditions.base import ConditionChecklist, WarningSign

CHECKLIST = ConditionChecklist(
    name="post_surgical",
    display_name="Post-Surgical Recovery",
    intro_questions=(
        "How are you feeling today, in your own words?",
        "How is the wound or the area around your operation looking and feeling?",
        "Any fever, or redness, swelling, or fluid coming from the wound?",
        "Are you managing to take your medicines as usual?",
    ),
    warning_signs=(
        # ---- URGENT: escalate immediately (nurse contacts now) ----
        WarningSign(
            id="heavy_bleeding",
            description="Heavy or uncontrolled bleeding from the wound",
            severity="URGENT",
            keywords=(
                "bleeding a lot",
                "won't stop bleeding",
                "will not stop bleeding",
                "soaked through",
                "lots of blood",
                "lot of blood",
                "heavy bleeding",
                "bleeding heavily",
                "gushing",
                "pouring blood",
            ),
        ),
        WarningSign(
            id="wound_opening",
            description="The wound has opened up (dehiscence)",
            severity="URGENT",
            keywords=(
                "wound has opened",
                "wound opened",
                "wound is opening",
                "opening up",
                "split open",
                "come apart",
                "came apart",
                "stitches came",
                "burst open",
                "gaping",
            ),
        ),
        WarningSign(
            id="clot_signs",
            description="Sudden breathlessness or chest pain, or a hot swollen painful calf (possible blood clot)",
            severity="URGENT",
            keywords=(
                "chest pain",
                "chest hurts",
                "pain in my chest",
                "can't breathe",
                "cannot breathe",
                "struggling to breathe",
                "sudden shortness of breath",
                "gasping",
                "calf is swollen",
                "calf is painful",
                "calf pain",
                "leg is hot and swollen",
            ),
        ),
        WarningSign(
            id="severe_infection",
            description="High fever with feeling very unwell (possible serious infection / sepsis)",
            severity="URGENT",
            keywords=(
                "very unwell",
                "very ill",
                "can't stop shaking",
                "shaking and sweating",
                "rigors",
                "feeling faint",
                "nearly fainted",
                "passing out",
                "passed out",
                "collapsed",
                "confused",
                "disoriented",
            ),
        ),
        # ---- WARNING: flag nurse for same-day callback ----
        WarningSign(
            id="wound_infection",
            description="Signs of wound infection — spreading redness, warmth, swelling, or discharge at the wound",
            severity="WARNING",
            keywords=(
                "is red",
                "gone red",
                "looks red",
                "getting red",
                "red around",
                "redness",
                "warm around",
                "hot around",
                "pus",
                "oozing",
                "weeping",
                "discharge from",
                "yellow discharge",
                "green discharge",
                "smells bad",
                "smelly",
                "swelling around the wound",
                "wound is swollen",
            ),
        ),
        WarningSign(
            id="fever",
            description="Fever or raised temperature (possible infection)",
            severity="WARNING",
            keywords=(
                "fever",
                "feverish",
                "high temperature",
                "temperature is up",
                "burning up",
                "hot and cold",
                "chills",
                "shivering",
            ),
        ),
        WarningSign(
            id="worsening_pain",
            description="Pain getting worse instead of better, or not controlled by pain relief",
            severity="WARNING",
            # NOTE: deliberately no bare "pain"/"sore" — some soreness is
            # normal early after surgery; the sign is *worsening* pain.
            keywords=(
                "more pain",
                "pain is worse",
                "worse pain",
                "more painful",
                "getting more painful",
                "pain is getting worse",
                "hurts more",
                "unbearable",
                "painkillers aren't working",
                "pain relief isn't working",
            ),
        ),
        WarningSign(
            id="persistent_vomiting",
            description="Ongoing sickness — vomiting or unable to keep food or fluids down",
            severity="WARNING",
            keywords=(
                "vomiting",
                "throwing up",
                "being sick",
                "keep being sick",
                "keep vomiting",
                "can't keep food",
                "can't keep anything down",
                "can't keep fluids",
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
