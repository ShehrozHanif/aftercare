"""Shared checklist structures + the deterministic sign matcher.

This module holds the *mechanism* only. All clinical content (the actual
warning signs, keywords, questions) lives in the per-condition checklist
modules — the engine never hardcodes clinical logic (CLAUDE.md §2.7, §6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Severity = Literal["OK", "WARNING", "URGENT"]


@dataclass(frozen=True)
class WarningSign:
    id: str
    description: str
    severity: Literal["WARNING", "URGENT"]
    # Plain-language phrases the deterministic matcher looks for.
    keywords: tuple[str, ...]
    # Signs like medication non-adherence are *expressed* with negations
    # ("not taking my medicines"), so the negation guard must be skipped.
    negation_aware: bool = True


@dataclass(frozen=True)
class ConditionChecklist:
    name: str
    display_name: str
    intro_questions: tuple[str, ...]
    warning_signs: tuple[WarningSign, ...]
    implemented: bool = True  # stubs register with False


_CLAUSE_SPLIT = re.compile(r"[.,;!?\n]| and | but | although | though ")

# Words that indicate the patient is *denying* a symptom in a clause.
# Matched on word boundaries so "cannot"/"can't" never count as denials —
# "can't breathe" / "cannot do my shopping" are affirmations of symptoms.
# Apostrophes optional ("dont") since patients type informally.
_NEGATION_RE = re.compile(
    r"\b(?:no|not|never|without|denies|deny|"
    r"don'?t|doesn'?t|hasn'?t|haven'?t|isn'?t|aren'?t|won'?t)\b"
)


def _is_negated(clause: str) -> bool:
    return _NEGATION_RE.search(clause) is not None


def match_signs(
    checklist: ConditionChecklist, text: str
) -> tuple[Severity, list[WarningSign]]:
    """Deterministic, clause-aware keyword match of ``text`` against the
    checklist. Returns the overall severity and the matched signs.

    Biased toward escalation: any single matched sign flags; negation
    handling only suppresses clearly denied symptoms ("no swelling").
    """
    clauses = [c.strip() for c in _CLAUSE_SPLIT.split(text.lower()) if c.strip()]
    matched: list[WarningSign] = []
    for sign in checklist.warning_signs:
        for clause in clauses:
            hit = False
            for keyword in sign.keywords:
                if keyword not in clause:
                    continue
                # Check negation on the clause *minus* the keyword itself,
                # so keywords that contain negation words ("no energy")
                # are not suppressed by their own text.
                remainder = clause.replace(keyword, " ")
                if sign.negation_aware and _is_negated(remainder):
                    continue
                hit = True
                break
            if hit:
                matched.append(sign)
                break
    if any(sign.severity == "URGENT" for sign in matched):
        return "URGENT", matched
    if matched:
        return "WARNING", matched
    return "OK", matched
