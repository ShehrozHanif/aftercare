"""CONDITIONS registry — adding a condition = adding one checklist module
here. The agent engine never changes (CLAUDE.md §6)."""

from app.agent.conditions.base import (
    ConditionChecklist,
    Severity,
    WarningSign,
    match_signs,
)
from app.agent.conditions.copd import CHECKLIST as copd
from app.agent.conditions.heart_failure import CHECKLIST as heart_failure
from app.agent.conditions.post_surgical import CHECKLIST as post_surgical

CONDITIONS: dict[str, ConditionChecklist] = {
    checklist.name: checklist
    for checklist in (heart_failure, post_surgical, copd)
}


class UnknownConditionError(LookupError):
    pass


def get_checklist(name: str) -> ConditionChecklist:
    try:
        return CONDITIONS[name]
    except KeyError:
        raise UnknownConditionError(
            f"No checklist registered for condition {name!r}"
        ) from None


__all__ = [
    "CONDITIONS",
    "ConditionChecklist",
    "Severity",
    "UnknownConditionError",
    "WarningSign",
    "get_checklist",
    "match_signs",
]
