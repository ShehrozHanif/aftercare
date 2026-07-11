"""Synthetic demo patients (CLAUDE.md §2.6: synthetic data only, ever).

Idempotent: runs on startup and does nothing if patients already exist.
Ahmed is the heart-failure demo patient from the §13 demo script — he is
seeded with his scripted Day-1/Day-2 all-clear check-ins so the dashboard
opens with visible history ("memory across days") and the stage demo
starts at the Day-4 escalation moment.
"""

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.conditions import CONDITIONS
from app.models import Condition, Conversation, Message, Patient

logger = logging.getLogger("aftercare.seed")


def _evening(days_ago: int) -> datetime:
    """A consistent evening check-in time, days_ago days back (UTC)."""
    day = date.today() - timedelta(days=days_ago)
    return datetime.combine(day, time(hour=18, minute=0), tzinfo=timezone.utc)


async def _seed_conversation(
    session: AsyncSession,
    patient: Patient,
    days_ago: int,
    turns: list[tuple[str, str]],  # (sender, text), in order
) -> None:
    started = _evening(days_ago)
    conversation = Conversation(patient_id=patient.id, started_at=started)
    session.add(conversation)
    await session.flush()
    for i, (sender, text) in enumerate(turns):
        session.add(
            Message(
                conversation_id=conversation.id,
                sender=sender,
                text=text,
                created_at=started + timedelta(minutes=i),
            )
        )
    await session.flush()


async def seed(session: AsyncSession) -> None:
    # Conditions sync from the code registry (idempotent).
    existing = set(
        (await session.execute(select(Condition.name))).scalars().all()
    )
    for checklist in CONDITIONS.values():
        if checklist.name not in existing:
            session.add(
                Condition(name=checklist.name, display_name=checklist.display_name)
            )
    await session.flush()

    patient_count = (
        await session.execute(select(func.count()).select_from(Patient))
    ).scalar_one()
    if patient_count:
        await session.commit()
        return

    from app.config import get_settings

    demo_phone = get_settings().demo_whatsapp_phone.strip() or None

    today = date.today()
    ahmed = Patient(
        name="Ahmed Raza",
        condition="heart_failure",
        discharge_date=today - timedelta(days=4),
        channel="whatsapp" if demo_phone else "web",
        phone=demo_phone,
        status="good",
    )
    fatima = Patient(
        name="Fatima Noor",
        condition="post_surgical",
        discharge_date=today - timedelta(days=2),
        channel="web",
        status="good",
    )
    bilal = Patient(
        name="Bilal Khan",
        condition="copd",
        discharge_date=today - timedelta(days=6),
        channel="web",
        status="good",
    )
    session.add_all([ahmed, fatima, bilal])
    await session.flush()

    # Ahmed's scripted Day-1 and Day-2 all-clear check-ins (jounry.md).
    # The stage demo then plays Day 4 live: the escalation lands on top of
    # visible, calm history.
    await _seed_conversation(
        session,
        ahmed,
        days_ago=3,
        turns=[
            ("agent", "Hi Ahmed 👋 This is your check-in from City Hospital. Just 2 minutes to see how your recovery's going. How are you feeling today?"),
            ("patient", "Okay I think. A bit tired."),
            ("agent", "That's normal in the first days. A few quick questions — any swelling in your legs or ankles?"),
            ("patient", "No"),
            ("agent", "Any trouble breathing?"),
            ("patient", "No"),
            ("agent", "Are you managing to take your medicines?"),
            ("patient", "Yes"),
            ("agent", "Wonderful — sounds like you're recovering well. I'll check in tomorrow. Message me anytime if anything changes. Take care, Ahmed 💙"),
        ],
    )
    await _seed_conversation(
        session,
        ahmed,
        days_ago=2,
        turns=[
            ("agent", "Hi Ahmed 👋 Quick check-in from City Hospital. How are you feeling today?"),
            ("patient", "Feeling a little better today. Walked to the shop."),
            ("agent", "That's great progress. Any swelling in your legs or ankles?"),
            ("patient", "No"),
            ("agent", "And your medicines — all taken as usual?"),
            ("patient", "Yes"),
            ("agent", "Perfect. Keep it up, Ahmed — I'll check in again tomorrow 💙"),
        ],
    )
    await _seed_conversation(
        session,
        fatima,
        days_ago=1,
        turns=[
            ("agent", "Hi Fatima 👋 This is your check-in from City Hospital. How are you feeling after your surgery?"),
            ("patient", "The wound is a little sore but I'm okay."),
            ("agent", "Some soreness is expected. Any fever, or redness around the wound?"),
            ("patient", "No"),
            ("agent", "Good to hear. Rest well — I'll check in again tomorrow 💙"),
        ],
    )
    await session.commit()
    logger.info(
        "Seeded synthetic demo patients (Ahmed, Fatima, Bilal) with scripted history"
    )
