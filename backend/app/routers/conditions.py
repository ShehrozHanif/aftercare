"""Condition-protocol routes — expose the pluggable checklists so the
dashboard can show they are real, inspectable clinical content (the core
'a new disease is a new checklist' pitch, made verifiable)."""

from fastapi import APIRouter

from app.agent.conditions import CONDITIONS
from app.schemas import ConditionOut, ConditionSigns

router = APIRouter(tags=["conditions"])


@router.get("/conditions", response_model=list[ConditionOut])
async def list_conditions() -> list[ConditionOut]:
    """All registered condition protocols with their warning signs grouped
    by severity. Content lives in code (the checklist registry), so no DB
    access is needed."""
    out: list[ConditionOut] = []
    for checklist in CONDITIONS.values():
        urgent = [
            s.description for s in checklist.warning_signs if s.severity == "URGENT"
        ]
        warning = [
            s.description for s in checklist.warning_signs if s.severity == "WARNING"
        ]
        out.append(
            ConditionOut(
                name=checklist.name,
                display_name=checklist.display_name,
                implemented=checklist.implemented,
                intro_questions=list(checklist.intro_questions),
                signs=ConditionSigns(urgent=urgent, warning=warning),
            )
        )
    return out
