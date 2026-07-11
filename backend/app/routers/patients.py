"""Dashboard-facing patient routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.conditions import CONDITIONS
from app.db import get_session
from app.models import Conversation, Message, Patient
from app.schemas import AlertOut, ConversationTranscript, MessageOut, PatientOut

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
