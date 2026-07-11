"""Pydantic v2 schemas — validation at every API boundary."""

from datetime import date, datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer


def _serialize_utc(dt: datetime) -> str:
    """All stored datetimes are UTC, but SQLite round-trips them naive —
    stamp the offset back on so browsers don't parse them as local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_serialize_utc, return_type=str)]


class ChatRequest(BaseModel):
    patient_id: int
    message: str = Field(min_length=1, max_length=4000)


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    conversation_id: int | None = None
    severity: str
    reason: str
    matched_signs: list[str] = []
    status: str
    created_at: UTCDateTime


class ChatResponse(BaseModel):
    reply: str
    alert: AlertOut | None = None


class CheckinStartResponse(BaseModel):
    conversation_id: int
    reply: str


class PatientOut(BaseModel):
    id: int
    name: str
    condition: str
    condition_display_name: str
    status: str
    channel: str
    discharge_date: date | None = None
    created_at: UTCDateTime
    open_alerts: list[AlertOut] = []


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender: str
    text: str
    created_at: UTCDateTime
    meta: dict | None = None


class ConversationTranscript(BaseModel):
    patient_id: int
    patient_name: str
    messages: list[MessageOut]


class CheckinSummary(BaseModel):
    """One row of the nurse-facing 'recent check-ins' history."""

    conversation_id: int
    started_at: UTCDateTime
    escalated: bool
    severity: str | None = None  # 'WARNING' | 'URGENT' when escalated
    summary: str
