"""COPD checklist — STRUCTURAL STUB.

Registered so the pluggable-condition design visibly scales (CLAUDE.md §6).
Adding the real protocol = filling in ``warning_signs`` from clinician-
reviewed discharge guidance. No engine changes needed.
"""

from app.agent.conditions.base import ConditionChecklist

CHECKLIST = ConditionChecklist(
    name="copd",
    display_name="COPD",
    intro_questions=(
        "How are you feeling today, in your own words?",
        "How is your breathing compared with yesterday?",
        "Are you managing to take your medicines and inhalers as usual?",
    ),
    warning_signs=(),  # TODO: clinician-reviewed signs (sputum, breathlessness...)
    implemented=False,
)
