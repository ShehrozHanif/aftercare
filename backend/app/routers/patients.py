"""Dashboard-facing patient routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from datetime import UTC, date, datetime

from app.agent.conditions import CONDITIONS
from app.db import get_session
from app.models import Alert, Conversation, Message, Patient
from app.schemas import (
    AlertOut,
    CheckinSummary,
    CheckinTodayItem,
    ConversationTranscript,
    DashboardStats,
    MessageOut,
    PatientOut,
    RecoveryReport,
    SymptomMention,
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


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    session: AsyncSession = Depends(get_session),
) -> DashboardStats:
    """Live control-room counters for the dashboard stat bar: how many
    patients are being followed, how many need a call right now (any open
    alert), and how many check-ins have gone out today."""
    patients = (
        (await session.execute(select(Patient).options(selectinload(Patient.alerts))))
        .scalars()
        .all()
    )
    needs_call = sum(
        1 for p in patients if any(a.status == "open" for a in p.alerts)
    )

    today = datetime.now(UTC).date()
    started = (
        (await session.execute(select(Conversation.started_at))).scalars().all()
    )
    checkins_today = sum(
        1
        for s in started
        if (s if s.tzinfo else s.replace(tzinfo=UTC)).astimezone(UTC).date() == today
    )

    return DashboardStats(
        patients_monitored=len(patients),
        needs_call=needs_call,
        checkins_today=checkins_today,
    )


@router.get("/checkins/today", response_model=list[CheckinTodayItem])
async def checkins_today(
    session: AsyncSession = Depends(get_session),
) -> list[CheckinTodayItem]:
    """Who has checked in today, newest first, with each patient's outcome —
    so the 'Check-ins today' counter drills down into an actual worklist."""
    today = datetime.now(UTC).date()
    conversations = (
        (
            await session.execute(
                select(Conversation).order_by(Conversation.started_at.desc())
            )
        )
        .scalars()
        .all()
    )
    today_convs = [
        c
        for c in conversations
        if (
            c.started_at
            if c.started_at.tzinfo
            else c.started_at.replace(tzinfo=UTC)
        ).astimezone(UTC).date()
        == today
    ]

    items: list[CheckinTodayItem] = []
    for conv in today_convs:
        patient = await session.get(Patient, conv.patient_id)
        if patient is None:
            continue
        answered = (
            await session.execute(
                select(Message.id)
                .where(
                    Message.conversation_id == conv.id,
                    Message.sender == "patient",
                )
                .limit(1)
            )
        ).scalar_one_or_none() is not None
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
        items.append(
            CheckinTodayItem(
                patient_id=patient.id,
                patient_name=patient.name,
                condition_display_name=_display_name(patient.condition),
                started_at=conv.started_at,
                answered=answered,
                escalated=alert is not None,
                severity=alert.severity if alert else None,
            )
        )
    return items


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


@router.post("/patients/{patient_id}/resolve", response_model=PatientOut)
async def resolve_patient(
    patient_id: int, session: AsyncSession = Depends(get_session)
) -> PatientOut:
    """Nurse closes the case: watch -> good, acknowledged alerts ->
    resolved. Refused while any alert is still open (acknowledge first —
    red never jumps straight to green). The asymmetry is deliberate: the
    agent can only raise concern; only a human can lower it (§2.2)."""
    patient = await session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    alerts = (
        (
            await session.execute(
                select(Alert).where(Alert.patient_id == patient_id)
            )
        )
        .scalars()
        .all()
    )
    if any(a.status == "open" for a in alerts):
        raise HTTPException(
            status_code=409,
            detail="Open alerts must be acknowledged before resolving",
        )

    for alert in alerts:
        if alert.status == "acknowledged":
            alert.status = "resolved"
    patient.status = "good"
    await session.commit()

    return PatientOut(
        id=patient.id,
        name=patient.name,
        condition=patient.condition,
        condition_display_name=_display_name(patient.condition),
        status=patient.status,
        channel=patient.channel,
        discharge_date=patient.discharge_date,
        created_at=patient.created_at,
        open_alerts=[],
    )


@router.get("/patients/{patient_id}/report", response_model=RecoveryReport)
async def recovery_report(
    patient_id: int, session: AsyncSession = Depends(get_session)
) -> RecoveryReport:
    """Post-discharge recovery report for the nurse: check-in compliance,
    symptom timeline, medication concerns, alert history. Deterministic —
    aggregates what the patient reported; never interprets clinical data."""
    patient = await session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    conversations = (
        (
            await session.execute(
                select(Conversation)
                .where(Conversation.patient_id == patient_id)
                .order_by(Conversation.started_at)
            )
        )
        .scalars()
        .all()
    )
    answered_ids = set(
        (
            await session.execute(
                select(Message.conversation_id)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(
                    Conversation.patient_id == patient_id,
                    Message.sender == "patient",
                )
                .distinct()
            )
        )
        .scalars()
        .all()
    )
    alerts = (
        (
            await session.execute(
                select(Alert)
                .where(Alert.patient_id == patient_id)
                .order_by(Alert.created_at)
            )
        )
        .scalars()
        .all()
    )

    return RecoveryReport(
        patient_id=patient.id,
        patient_name=patient.name,
        condition_display_name=_display_name(patient.condition),
        discharge_date=patient.discharge_date,
        days_since_discharge=(
            (date.today() - patient.discharge_date).days
            if patient.discharge_date
            else None
        ),
        status=patient.status,
        checkins_sent=len(conversations),
        checkins_answered=len(answered_ids),
        medication_concerns=sum(
            1
            for a in alerts
            if any("medication" in sign.lower() for sign in (a.matched_signs or []))
        ),
        symptom_mentions=[
            SymptomMention(
                date=a.created_at,
                severity=a.severity,
                signs=list(a.matched_signs or []),
            )
            for a in alerts
        ],
        alerts_total=len(alerts),
        alerts_open=sum(1 for a in alerts if a.status == "open"),
        generated_at=datetime.now(UTC),
    )
