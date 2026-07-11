"""Synthetic demo patients (CLAUDE.md §2.6: synthetic data only, ever).

Idempotent: runs on startup and does nothing if patients already exist.
Ahmed is the heart-failure demo patient from the §13 demo script.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.conditions import CONDITIONS
from app.models import Condition, Patient

logger = logging.getLogger("aftercare.seed")


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

    today = date.today()
    session.add_all(
        [
            Patient(
                name="Ahmed Raza",
                condition="heart_failure",
                discharge_date=today - timedelta(days=4),
                channel="web",
                status="good",
            ),
            Patient(
                name="Fatima Noor",
                condition="post_surgical",
                discharge_date=today - timedelta(days=2),
                channel="web",
                status="good",
            ),
            Patient(
                name="Bilal Khan",
                condition="copd",
                discharge_date=today - timedelta(days=6),
                channel="web",
                status="good",
            ),
        ]
    )
    await session.commit()
    logger.info("Seeded synthetic demo patients (Ahmed, Fatima, Bilal)")
