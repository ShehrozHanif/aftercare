"""The five clinical tools from CLAUDE.md §8, exposed to the OpenAI
Agents SDK model.

IMPLEMENTATION NOTE (MCP framing): these are implemented as Agents SDK
*function tools* rather than a separate MCP server subprocess, because
every tool needs the request-scoped async SQLAlchemy session and patient
context — impractical to marshal across a stdio MCP boundary within the
hackathon window. The tool names, signatures, and contracts match the §8
MCP spec exactly, so promoting this module to a real MCP server later is
a transport change only.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from agents import RunContextWrapper, function_tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.conditions import get_checklist, match_signs
from app.models import Alert, Conversation, Message, Patient

logger = logging.getLogger("aftercare.agent.tools")

_VALID_SEVERITIES = ("WARNING", "URGENT")
_SEVERITY_RANK = {"WARNING": 1, "URGENT": 2}


@dataclass
class ToolContext:
    """Request-scoped context handed to every tool call."""

    session: AsyncSession
    patient: Patient
    conversation: Conversation
    patient_message: Message
    escalation: Alert | None = None
    # The SDK may issue parallel tool calls; without this lock two
    # concurrent escalate_to_clinician calls can both pass the
    # already-escalated check and create duplicate alerts.
    escalation_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


async def create_alert(
    session: AsyncSession,
    patient: Patient,
    conversation: Conversation | None,
    severity: str,
    reason: str,
    matched_signs: list[str],
) -> Alert:
    """Shared escalation implementation — used by both the LLM tool and
    the deterministic fallback path. Creates the alert and flips the
    patient's dashboard status to 'alert'.

    Dedup: while an OPEN alert of equal-or-higher severity exists for
    this patient, the nurse is already looking — a repeat escalation for
    the same episode returns that alert instead of spamming the
    dashboard. A genuine worsening (URGENT over an open WARNING) still
    creates a new alert."""
    severity = (severity or "").upper()
    if severity not in _VALID_SEVERITIES:
        # Bias toward escalation: an unrecognized severity still flags.
        logger.warning("Unrecognized severity %r — defaulting to WARNING", severity)
        severity = "WARNING"

    open_alerts = (
        (
            await session.execute(
                select(Alert)
                .where(Alert.patient_id == patient.id, Alert.status == "open")
                .order_by(Alert.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    for open_alert in open_alerts:
        if _SEVERITY_RANK[open_alert.severity] >= _SEVERITY_RANK[severity]:
            patient.status = "alert"  # keep the contract even on dedup
            logger.info(
                "Escalation deduplicated for patient_id=%s: open alert %s "
                "(%s) already covers severity %s",
                patient.id,
                open_alert.id,
                open_alert.severity,
                severity,
            )
            return open_alert

    alert = Alert(
        patient_id=patient.id,
        conversation_id=conversation.id if conversation else None,
        severity=severity,
        reason=reason,
        matched_signs=list(matched_signs),
        status="open",
    )
    patient.status = "alert"
    session.add(alert)
    await session.flush()
    logger.info(
        "ESCALATION patient_id=%s severity=%s alert_id=%s reason=%s",
        patient.id,
        severity,
        alert.id,
        reason,
    )
    return alert


# ---------------------------------------------------------------------------
# Tool 1: get_condition_checklist
# ---------------------------------------------------------------------------
@function_tool
async def get_condition_checklist(
    ctx: RunContextWrapper[ToolContext], condition: str
) -> dict:
    """Return the warning-sign checklist for a condition.

    Args:
        condition: Condition name, e.g. 'heart_failure'.
    """
    checklist = get_checklist(condition or ctx.context.patient.condition)
    return {
        "condition": checklist.name,
        "display_name": checklist.display_name,
        "intro_questions": list(checklist.intro_questions),
        "warning_signs": [
            {"id": s.id, "description": s.description, "severity": s.severity}
            for s in checklist.warning_signs
        ],
    }


# ---------------------------------------------------------------------------
# Tool 2: get_patient_history
# ---------------------------------------------------------------------------
@function_tool
async def get_patient_history(
    ctx: RunContextWrapper[ToolContext], patient_id: int
) -> dict:
    """Return the patient's prior messages and alerts (memory across days).

    Args:
        patient_id: The patient to look up. Scoped to the current
            check-in's patient regardless of the value passed.
    """
    # Security: always scope to the patient of this check-in.
    patient = ctx.context.patient
    session = ctx.context.session

    messages = (
        await session.execute(
            select(Message.sender, Message.text, Message.created_at)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.patient_id == patient.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(30)
        )
    ).all()
    alerts = (
        await session.execute(
            select(Alert.severity, Alert.reason, Alert.status, Alert.created_at)
            .where(Alert.patient_id == patient.id)
            .order_by(Alert.created_at.desc())
            .limit(10)
        )
    ).all()
    return {
        "patient_id": patient.id,
        "messages": [
            {"sender": m.sender, "text": m.text, "at": m.created_at.isoformat()}
            for m in reversed(messages)
        ],
        "alerts": [
            {
                "severity": a.severity,
                "reason": a.reason,
                "status": a.status,
                "at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
    }


# ---------------------------------------------------------------------------
# Tool 3: log_response
# ---------------------------------------------------------------------------
@function_tool
async def log_response(
    ctx: RunContextWrapper[ToolContext], patient_id: int, text: str
) -> dict:
    """Persist a short structured summary of what the patient reported.

    Args:
        patient_id: The patient this log belongs to.
        text: Structured summary, e.g. 'swelling: yes (ankles, new); breathlessness: on exertion'.
    """
    message = ctx.context.patient_message
    meta = dict(message.meta or {})
    meta.setdefault("structured_log", []).append(text)
    message.meta = meta
    await ctx.context.session.flush()
    return {"status": "logged"}


# ---------------------------------------------------------------------------
# Tool 4: classify_severity
# ---------------------------------------------------------------------------
@function_tool
async def classify_severity(
    ctx: RunContextWrapper[ToolContext], text: str, condition: str
) -> dict:
    """Deterministic keyword classification of a message against the
    condition checklist. Helper only — if your own reading is MORE
    cautious than this result, trust your reading.

    Args:
        text: The patient's message.
        condition: Condition name, e.g. 'heart_failure'.
    """
    checklist = get_checklist(condition or ctx.context.patient.condition)
    severity, signs = match_signs(checklist, text)
    return {
        "severity": severity,
        "matched_signs": [
            {"id": s.id, "description": s.description, "severity": s.severity}
            for s in signs
        ],
    }


# ---------------------------------------------------------------------------
# Tool 5: escalate_to_clinician (the money action)
# ---------------------------------------------------------------------------
@function_tool
async def escalate_to_clinician(
    ctx: RunContextWrapper[ToolContext],
    patient_id: int,
    severity: str,
    reason: str,
    matched_signs: list[str],
) -> dict:
    """Flag a human nurse: creates an alert on the care-team dashboard and
    marks the patient as needing attention. Call whenever any URGENT or
    WARNING sign — or anything else worrying — appears.

    Args:
        patient_id: The patient to escalate.
        severity: 'WARNING' (same-day nurse callback) or 'URGENT' (nurse contacts now).
        reason: Short factual summary for the nurse (what the patient reported).
        matched_signs: The checklist sign descriptions that matched.
    """
    context = ctx.context
    normalized = (severity or "").upper()
    async with context.escalation_lock:
        if context.escalation is not None:
            # Already escalated this turn — upgrade severity if needed.
            if normalized == "URGENT" and context.escalation.severity != "URGENT":
                context.escalation.severity = "URGENT"
                context.escalation.reason = reason
                await context.session.flush()
            return {
                "status": "already_escalated",
                "severity": context.escalation.severity,
                "alert_id": context.escalation.id,
            }
        alert = await create_alert(
            context.session,
            context.patient,
            context.conversation,
            normalized,
            reason,
            matched_signs,
        )
        context.escalation = alert
    return {"status": "escalated", "severity": alert.severity, "alert_id": alert.id}
