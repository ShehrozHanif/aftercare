"""Pydantic v2 schemas — validation at every API boundary."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


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
    created_at: datetime


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
    created_at: datetime
    open_alerts: list[AlertOut] = []


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender: str
    text: str
    created_at: datetime
    meta: dict | None = None


class ConversationTranscript(BaseModel):
    patient_id: int
    patient_name: str
    messages: list[MessageOut]
