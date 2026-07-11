"""WhatsApp door (CLAUDE.md §8, Phase 4 bonus) — Twilio sandbox webhook.

Same brain, different door: maps the sender's number to a patient and
runs the exact same agent_turn as web chat. The reply goes back as TwiML
in the webhook response (works in the sandbox without REST credentials).
Unknown numbers get a polite pointer, never an error page.
"""

import logging
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import agent_turn
from app.db import get_session
from app.models import Patient

router = APIRouter(tags=["whatsapp"])
logger = logging.getLogger("aftercare.whatsapp")

UNKNOWN_NUMBER_REPLY = (
    "Hi! This number isn't linked to an AfterCare check-in yet. "
    "Please contact your hospital's care team to get set up."
)


def _twiml(body: str) -> Response:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(body)}</Message></Response>"
    )
    return Response(content=xml, media_type="application/xml")


def _normalize(number: str) -> str:
    """'whatsapp:+9230...' -> '+9230...'"""
    return number.removeprefix("whatsapp:").strip()


@router.post("/whatsapp/incoming")
async def whatsapp_incoming(
    From: str = Form(default=""),
    Body: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
) -> Response:
    phone = _normalize(From)
    text = Body.strip()
    if not phone or not text:
        return _twiml(UNKNOWN_NUMBER_REPLY)

    patient = (
        await session.execute(select(Patient).where(Patient.phone == phone).limit(1))
    ).scalar_one_or_none()
    if patient is None:
        logger.info("WhatsApp from unlinked number %s", phone)
        return _twiml(UNKNOWN_NUMBER_REPLY)

    result = await agent_turn(session, patient, text)
    return _twiml(result.reply)
