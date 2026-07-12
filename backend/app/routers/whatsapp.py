"""WhatsApp door (CLAUDE.md §8, Phase 4 bonus) — Twilio sandbox webhook.

Same brain, different door: maps the sender's number to a patient and
runs the exact same agent_turn as web chat.

Reply delivery, two modes:
- Twilio configured (live): acknowledge the webhook INSTANTLY with empty
  TwiML, run the agent in a background task, and deliver the reply via
  the REST API. Twilio abandons webhooks after ~15s (error 11200) and an
  LLM turn can take longer — a synchronous TwiML reply times out.
- Twilio not configured (tests/dev): reply synchronously as TwiML in the
  webhook response, which needs no credentials.

Unknown numbers get a polite pointer, never an error page.
"""

import asyncio
import logging
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import agent_turn
from app.db import SessionLocal, get_session
from app.models import Patient
from app.services import twilio_client

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


_EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'

# Keep strong references so background turns aren't garbage-collected.
_pending_turns: set[asyncio.Task] = set()


async def _process_and_reply(patient_id: int, text: str) -> None:
    """Run the agent turn on its own DB session and deliver the reply
    over WhatsApp. Runs outside the webhook request lifecycle."""
    async with SessionLocal() as session:
        patient = await session.get(Patient, patient_id)
        if patient is None:
            return
        try:
            result = await agent_turn(session, patient, text)
        except Exception:
            logger.exception(
                "WhatsApp background turn failed for patient_id=%s", patient_id
            )
            return
        if patient.phone:
            await twilio_client.send_whatsapp(patient.phone, result.reply)


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

    if twilio_client.is_configured():
        # Ack instantly; reply via REST when the agent is done (§ module doc).
        task = asyncio.create_task(_process_and_reply(patient.id, text))
        _pending_turns.add(task)
        task.add_done_callback(_pending_turns.discard)
        return Response(content=_EMPTY_TWIML, media_type="application/xml")

    result = await agent_turn(session, patient, text)
    return _twiml(result.reply)
