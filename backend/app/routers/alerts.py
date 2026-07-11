"""Nurse alert actions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Alert, Patient
from app.schemas import AlertOut

router = APIRouter(tags=["alerts"])


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: int, session: AsyncSession = Depends(get_session)
) -> AlertOut:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "acknowledged"

    # If no other alerts remain open, drop the patient from 'alert' to
    # 'watch' (a nurse has eyes on them; not yet back to 'good').
    remaining_open = (
        await session.execute(
            select(Alert.id).where(
                Alert.patient_id == alert.patient_id,
                Alert.status == "open",
                Alert.id != alert.id,
            )
        )
    ).first()
    if remaining_open is None:
        patient = await session.get(Patient, alert.patient_id)
        if patient is not None and patient.status == "alert":
            patient.status = "watch"

    await session.commit()
    return AlertOut.model_validate(alert)
