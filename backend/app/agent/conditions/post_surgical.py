"""Post-surgical recovery checklist — STRUCTURAL STUB.

Registered so the pluggable-condition design visibly scales (CLAUDE.md §6).
Adding the real protocol = filling in ``warning_signs`` from clinician-
reviewed discharge guidance. No engine changes needed.
"""

from app.agent.conditions.base import ConditionChecklist

CHECKLIST = ConditionChecklist(
    name="post_surgical",
    display_name="Post-Surgical Recovery",
    intro_questions=(
        "How are you feeling today, in your own words?",
        "How is the area around your operation feeling?",
        "Are you managing to take your medicines as usual?",
    ),
    warning_signs=(),  # TODO: clinician-reviewed signs (wound, fever, pain...)
    implemented=False,
)
