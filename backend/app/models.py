"""SQLAlchemy models per CLAUDE.md §8 data model."""

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Condition(Base):
    """Condition row — the checklist logic itself lives in the code registry
    (``app/agent/conditions/``), keyed by ``name``."""

    __tablename__ = "conditions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    condition: Mapped[str] = mapped_column(ForeignKey("conditions.name"))
    discharge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    channel: Mapped[str] = mapped_column(String(16), default="web")  # 'web'|'whatsapp'
    status: Mapped[str] = mapped_column(String(16), default="good")  # 'good'|'watch'|'alert'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="patient")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="patient")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    sender: Mapped[str] = mapped_column(String(16))  # 'agent'|'patient'
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String(16))  # 'WARNING'|'URGENT'
    reason: Mapped[str] = mapped_column(Text)
    matched_signs: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="open")  # 'open'|'acknowledged'|'resolved'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="alerts")
    conversation: Mapped[Conversation | None] = relationship()
