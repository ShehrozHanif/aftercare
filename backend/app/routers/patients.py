"""Dashboard-facing patient routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.conditions import CONDITIONS
from app.db import get_session
from app.models import Alert, Conversation, Message, Patient
from app.schemas import (
    AlertOut,
    CheckinSummary,
    ConversationTranscript,
    MessageOut,
    PatientOut,
)

router = APIRouter(tags=["patients"])


def _display_name(condition: str) -> str:
    checklist = CONDITIONS.get(condition)
    return checklist.display_name if checklist else condition


@router.get("/patients", response_model=list[PatientOut])
async def list_patients(
    session: AsyncSession = Depends(get_session),
) -> list[PatientOut]:
    patients = (
        (
            await session.execute(
                select(Patient)
                .options(selectinload(Patient.alerts))
                .order_by(Patient.id)
            )
        )
        .scalars()
        .all()
    )
    return [
        PatientOut(
            id=p.id,
            name=p.name,
            condition=p.condition,
            condition_display_name=_display_name(p.condition),
            status=p.status,
            channel=p.channel,
            discharge_date=p.discharge_date,
            created_at=p.created_at,
            open_alerts=[
                AlertOut.model_validate(a) for a in p.alerts if a.status == "open"
            ],
        )
        for p in patients
    ]


@router.get(
    "/patients/{patient_id}/conversation", response_model=ConversationTranscript
)
async def get_conversation(
    patient_id: int, session: AsyncSession = Depends(get_session)
) -> ConversationTranscript:
    patient = await session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    messages = (
        (
            await session.execute(
                select(Message)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(Conversation.patient_id == patient_id)
                .order_by(Message.created_at, Message.id)
            )
        )
        .scalars()
        .all()
    )
    return ConversationTranscript(
        patient_id=patient.id,
        patient_name=patient.name,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.get("/patients/{patient_id}/checkins", response_model=list[CheckinSummary])
async def list_checkins(
    patient_id: int, session: AsyncSession = Depends(get_session)
) -> list[CheckinSummary]:
    """Recent check-in history for the nurse view — one row per
    conversation with its outcome, so the trajectory across days is
    visible at a glance (the agent's memory, surfaced)."""
    patient = await session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    conversations = (
        (
            await session.execute(
                select(Conversation)
                .where(Conversation.patient_id == patient_id)
                .order_by(Conversation.started_at.desc(), Conversation.id.desc())
                .limit(14)
            )
        )
        .scalars()
        .all()
    )

    summaries: list[CheckinSummary] = []
    for conv in conversations:
        first_patient_text = (
            await session.execute(
                select(Message.text)
                .where(
                    Message.conversation_id == conv.id,
                    Message.sender == "patient",
                )
                .order_by(Message.created_at, Message.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        alert = (
            (
                await session.execute(
                    select(Alert)
                    .where(Alert.conversation_id == conv.id)
                    .order_by(Alert.created_at.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        summaries.append(
            CheckinSummary(
                conversation_id=conv.id,
                started_at=conv.started_at,
                escalated=alert is not None,
                severity=alert.severity if alert else None,
                summary=(
                    alert.reason
                    if alert
                    else (first_patient_text or "Check-in started — no reply yet")
                ),
            )
        )
    return summaries
