"""Web-chat door + manual check-in trigger. Thin: validates, loads the
patient, delegates to the agent runner."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.conditions import UnknownConditionError
from app.agent.runner import agent_turn, start_checkin
from app.db import get_session
from app.models import Patient
from app.schemas import AlertOut, ChatRequest, ChatResponse, CheckinStartResponse
from app.services.twilio_client import send_whatsapp

router = APIRouter(tags=["chat"])


async def _load_patient(session: AsyncSession, patient_id: int) -> Patient:
    patient = await session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest, session: AsyncSession = Depends(get_session)
) -> ChatResponse:
    patient = await _load_patient(session, body.patient_id)
    try:
        result = await agent_turn(session, patient, body.message)
    except UnknownConditionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ChatResponse(
        reply=result.reply,
        alert=AlertOut.model_validate(result.alert) if result.alert else None,
    )


@router.post("/checkins/{patient_id}/start", response_model=CheckinStartResponse)
async def start_checkin_route(
    patient_id: int, session: AsyncSession = Depends(get_session)
) -> CheckinStartResponse:
    patient = await _load_patient(session, patient_id)
    try:
        conversation, greeting = await start_checkin(session, patient)
    except UnknownConditionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # WhatsApp door (Phase 4): deliver the greeting to the patient's phone
    # too. No-ops safely when Twilio isn't configured — web chat never
    # depends on it.
    if patient.channel == "whatsapp" and patient.phone:
        await send_whatsapp(patient.phone, greeting)
    return CheckinStartResponse(conversation_id=conversation.id, reply=greeting)
