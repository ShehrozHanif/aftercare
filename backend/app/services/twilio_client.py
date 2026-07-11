"""Twilio WhatsApp sandbox client (CLAUDE.md §8, Phase 4 bonus).

The ONLY WhatsApp-specific code lives here and in routers/whatsapp.py —
the agent stays channel-agnostic. Fallback rule: with no Twilio
credentials configured, everything degrades to a logged no-op and the
web-chat path is untouched.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings

logger = logging.getLogger("aftercare.twilio")


def is_configured() -> bool:
    s = get_settings()
    return bool(
        s.twilio_account_sid.strip()
        and s.twilio_auth_token.strip()
        and s.twilio_whatsapp_from.strip()
    )


def _send_sync(to: str, body: str) -> str:
    from twilio.rest import Client  # lazy: optional dependency path

    s = get_settings()
    client = Client(s.twilio_account_sid, s.twilio_auth_token)
    message = client.messages.create(
        from_=s.twilio_whatsapp_from,
        to=to if to.startswith("whatsapp:") else f"whatsapp:{to}",
        body=body,
    )
    return message.sid


async def send_whatsapp(to: str, body: str) -> str | None:
    """Send a WhatsApp message; returns the Twilio message SID, or None
    when Twilio isn't configured / the send fails (never raises — a
    failed WhatsApp send must not break the calling flow)."""
    if not is_configured():
        logger.warning("Twilio not configured — WhatsApp send to %s skipped", to)
        return None
    try:
        sid = await asyncio.to_thread(_send_sync, to, body)
        logger.info("WhatsApp sent to %s sid=%s", to, sid)
        return sid
    except Exception:
        logger.exception("WhatsApp send to %s failed", to)
        return None
