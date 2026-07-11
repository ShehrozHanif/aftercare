"""agent_turn — the one shared brain (CLAUDE.md §8 core service).

Channel-agnostic: callers (web chat router today, WhatsApp webhook in
Phase 4) pass a patient + incoming text and get back a reply + optional
alert. This module never knows which channel the message came from.

Two execution modes, logged explicitly per turn:
- LLM mode (primary): OpenAI Agents SDK with the five §8 clinical tools;
  the model decides to call escalate_to_clinician.
- Deterministic fallback: if OPENAI_API_KEY is unset (or the LLM call
  fails), a checklist-keyword classifier + templated calm replies keep
  the API and demo fully functional offline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import prompts
from app.agent.conditions import get_checklist, match_signs
from app.agent.conditions.base import ConditionChecklist
from app.agent.mcp.tools import ToolContext, create_alert
from app.config import get_settings
from app.models import Alert, Conversation, Message, Patient

logger = logging.getLogger("aftercare.agent")


@dataclass
class TurnResult:
    reply: str
    alert: Alert | None


async def agent_turn(
    session: AsyncSession, patient: Patient, incoming_text: str
) -> TurnResult:
    """Run one full check-in turn: persist the patient message, reason
    over it (LLM or fallback), escalate if needed, persist the reply."""
    checklist = get_checklist(patient.condition)
    conversation = await _get_or_create_conversation(session, patient)

    patient_message = Message(
        conversation_id=conversation.id, sender="patient", text=incoming_text
    )
    session.add(patient_message)
    await session.flush()

    settings = get_settings()
    tool_context = ToolContext(
        session=session,
        patient=patient,
        conversation=conversation,
        patient_message=patient_message,
    )
    if settings.openai_api_key.strip():
        logger.info("agent_turn mode=llm patient_id=%s", patient.id)
        try:
            reply, alert, mode = await _llm_turn(tool_context, checklist)
        except Exception:
            logger.exception(
                "LLM turn failed for patient_id=%s — falling back to the "
                "deterministic checklist classifier for this turn",
                patient.id,
            )
            if tool_context.escalation is not None:
                # The model escalated before the failure — keep that alert;
                # a fallback run here would create a duplicate.
                reply = prompts.calm_escalation_reply(patient)
                alert, mode = tool_context.escalation, "llm+template"
            else:
                reply, alert, mode = await _fallback_turn(
                    session, patient, conversation, checklist, incoming_text
                )
    else:
        logger.warning(
            "agent_turn mode=fallback patient_id=%s — OPENAI_API_KEY is not "
            "set; using the deterministic checklist classifier",
            patient.id,
        )
        reply, alert, mode = await _fallback_turn(
            session, patient, conversation, checklist, incoming_text
        )

    if alert is None:
        # Safety net (§2 rule 3 — over-flag, never under-flag): the model
        # can nondeterministically fail to call escalate_to_clinician on a
        # message the checklist unambiguously matches. The deterministic
        # classifier gets a veto in the escalating direction only.
        severity, signs = match_signs(checklist, incoming_text)
        if severity != "OK":
            descriptions = [sign.description for sign in signs]
            alert = await create_alert(
                session,
                patient,
                conversation,
                severity,
                "Checklist safety net: patient message matched discharge "
                f"warning signs: {'; '.join(descriptions)}. "
                f'Patient said: "{incoming_text.strip()}"',
                descriptions,
            )
            reply = prompts.calm_escalation_reply(patient)
            logger.warning(
                "SAFETY NET escalation patient_id=%s severity=%s — the %s "
                "path did not escalate a checklist-matching message",
                patient.id,
                severity,
                mode,
            )
            mode = f"{mode}+safety-net"

    if alert is not None:
        # §8 contract, enforced at one choke point regardless of which
        # path created the alert.
        patient.status = "alert"

    agent_message = Message(
        conversation_id=conversation.id,
        sender="agent",
        text=reply,
        meta={
            "mode": mode,
            "escalated": alert is not None,
            "severity": alert.severity if alert else "OK",
        },
    )
    session.add(agent_message)
    await session.commit()
    return TurnResult(reply=reply, alert=alert)


async def start_checkin(session: AsyncSession, patient: Patient) -> tuple[Conversation, str]:
    """Open a new conversation and send the agent's greeting (used by the
    manual/scheduled check-in trigger)."""
    checklist = get_checklist(patient.condition)
    conversation = Conversation(patient_id=patient.id)
    session.add(conversation)
    await session.flush()
    greeting = prompts.build_greeting(patient, checklist)
    session.add(
        Message(conversation_id=conversation.id, sender="agent", text=greeting)
    )
    await session.commit()
    return conversation, greeting


# ---------------------------------------------------------------------------
# LLM path (primary)
# ---------------------------------------------------------------------------
async def _llm_turn(
    tool_context: ToolContext, checklist: ConditionChecklist
) -> tuple[str, Alert | None, str]:
    from agents import Runner  # lazy: fallback mode must not depend on it

    from app.agent.mcp.server import build_agent

    session = tool_context.session
    patient = tool_context.patient
    conversation = tool_context.conversation
    patient_message = tool_context.patient_message

    agent = build_agent(patient, checklist)
    history = await _conversation_input(session, conversation, patient_message)
    result = await Runner.run(agent, input=history, context=tool_context)

    alert = tool_context.escalation
    reply = str(result.final_output).strip() if result.final_output else ""
    if not reply:
        # Never send an empty reply; on escalation always fall back to the
        # calm reassurance template (§2 rule 4).
        reply = (
            prompts.calm_escalation_reply(patient)
            if alert
            else prompts.all_clear_reply(patient)
        )
    return reply, alert, "llm"


async def _conversation_input(
    session: AsyncSession, conversation: Conversation, current: Message
) -> list[dict]:
    """Conversation history as Agents SDK input items (patient=user,
    agent=assistant), ending with the current patient message."""
    messages = (
        (
            await session.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation.id,
                    Message.id != current.id,
                )
                .order_by(Message.created_at, Message.id)
            )
        )
        .scalars()
        .all()
    )
    items = [
        {
            "role": "user" if m.sender == "patient" else "assistant",
            "content": m.text,
        }
        for m in messages
    ]
    items.append({"role": "user", "content": current.text})
    return items


# ---------------------------------------------------------------------------
# Deterministic fallback path (no API key / LLM failure)
# ---------------------------------------------------------------------------
async def _fallback_turn(
    session: AsyncSession,
    patient: Patient,
    conversation: Conversation,
    checklist: ConditionChecklist,
    incoming_text: str,
) -> tuple[str, Alert | None, str]:
    severity, signs = match_signs(checklist, incoming_text)
    if severity == "OK":
        return prompts.all_clear_reply(patient), None, "fallback"

    descriptions = [sign.description for sign in signs]
    reason = (
        f"Patient message matched discharge warning signs: "
        f"{'; '.join(descriptions)}. Patient said: \"{incoming_text.strip()}\""
    )
    alert = await create_alert(
        session, patient, conversation, severity, reason, descriptions
    )
    return prompts.calm_escalation_reply(patient), alert, "fallback"


async def _get_or_create_conversation(
    session: AsyncSession, patient: Patient
) -> Conversation:
    conversation = (
        await session.execute(
            select(Conversation)
            .where(Conversation.patient_id == patient.id)
            .order_by(Conversation.started_at.desc(), Conversation.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(patient_id=patient.id)
        session.add(conversation)
        await session.flush()
    return conversation
