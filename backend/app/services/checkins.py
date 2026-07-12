"""Phase 5 — scheduled daily check-ins.

A deliberately simple in-process scheduler (§4: no K8s/queues for one
small app): an asyncio task sleeps until the configured UTC hour, then
starts a check-in for every patient who hasn't had one today. The same
run function backs POST /checkins/run so the demo can fire it live.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import start_checkin
from app.config import get_settings
from app.models import Conversation, Patient
from app.services.twilio_client import send_whatsapp

logger = logging.getLogger("aftercare.scheduler")


async def start_and_deliver_checkin(
    session: AsyncSession, patient: Patient
) -> tuple[int, str]:
    """Start a check-in and deliver the greeting over the patient's
    channel. The agent stays channel-agnostic — delivery happens here."""
    conversation, greeting = await start_checkin(session, patient)
    if patient.channel == "whatsapp" and patient.phone:
        await send_whatsapp(patient.phone, greeting)
    return conversation.id, greeting


async def _has_checkin_today(session: AsyncSession, patient_id: int) -> bool:
    latest = (
        await session.execute(
            select(Conversation.started_at)
            .where(Conversation.patient_id == patient_id)
            .order_by(Conversation.started_at.desc(), Conversation.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None:
        return False
    if latest.tzinfo is None:  # SQLite returns naive; stored values are UTC
        latest = latest.replace(tzinfo=UTC)
    return latest.astimezone(UTC).date() == datetime.now(UTC).date()


async def run_due_checkins(session: AsyncSession) -> list[int]:
    """Start a check-in for every patient without one today (idempotent —
    safe to fire repeatedly). Returns the patient ids started."""
    patients = (
        (await session.execute(select(Patient).order_by(Patient.id))).scalars().all()
    )
    started: list[int] = []
    for patient in patients:
        if await _has_checkin_today(session, patient.id):
            continue
        await start_and_deliver_checkin(session, patient)
        started.append(patient.id)
    if started:
        logger.info("Daily check-ins started for patients %s", started)
    return started


def _seconds_until(hour_utc: int) -> float:
    now = datetime.now(UTC)
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def scheduler_loop() -> None:
    """Background task: fire the daily check-ins at the configured hour."""
    from app.db import SessionLocal  # lazy: engine is built at startup

    hour = get_settings().checkin_hour_utc
    logger.info("Daily check-in scheduler active (fires %02d:00 UTC)", hour)
    while True:
        await asyncio.sleep(_seconds_until(hour))
        try:
            async with SessionLocal() as session:
                await run_due_checkins(session)
        except Exception:
            # The scheduler must survive a bad run — next day still fires.
            logger.exception("Scheduled check-in run failed")
