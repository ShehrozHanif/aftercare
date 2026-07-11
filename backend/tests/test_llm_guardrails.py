"""Regression tests for the LLM-path guardrails in agent_turn:

1. Safety net — if the model path returns without escalating a message the
   checklist unambiguously matches, the deterministic classifier escalates.
2. No duplicate alerts — if the LLM run crashes *after* the escalation tool
   fired, the exception path must reuse that alert, not run the fallback.
3. Status contract — every escalating turn leaves patient.status == 'alert'.
"""

import pytest
from sqlalchemy import func, select

from app import models
from app.agent import runner
from app.agent.mcp.tools import create_alert
from app.agent.prompts import calm_escalation_reply
from app.config import get_settings
from tests.conftest import AHMED_ID, chat

RED_FLAG = "My ankles are swollen and I get out of breath climbing the stairs"


@pytest.fixture
def llm_mode(monkeypatch):
    """Pretend a key is configured so agent_turn takes the LLM branch."""
    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")


async def _alert_count(db_sessionmaker) -> int:
    async with db_sessionmaker() as session:
        return (await session.execute(select(func.count(models.Alert.id)))).scalar()


async def _patient_status(db_sessionmaker) -> str:
    async with db_sessionmaker() as session:
        return (await session.get(models.Patient, AHMED_ID)).status


@pytest.mark.anyio
async def test_safety_net_escalates_when_llm_underflags(
    client, db_sessionmaker, llm_mode, monkeypatch
):
    async def underflagging_llm(tool_context, checklist):
        return "Thanks for letting me know! Anything else?", None, "llm"

    monkeypatch.setattr(runner, "_llm_turn", underflagging_llm)

    data = await chat(client, RED_FLAG)

    assert data["alert"] is not None, "safety net must escalate a checklist match"
    assert data["alert"]["severity"] == "WARNING"
    # The under-flagging reply is replaced by the calm reassurance template.
    assert "care team" in data["reply"].lower()
    assert await _patient_status(db_sessionmaker) == "alert"


@pytest.mark.anyio
async def test_llm_crash_after_escalation_creates_no_duplicate(
    client, db_sessionmaker, llm_mode, monkeypatch
):
    async def escalate_then_crash(tool_context, checklist):
        tool_context.escalation = await create_alert(
            tool_context.session,
            tool_context.patient,
            tool_context.conversation,
            "WARNING",
            "Ankle swelling and exertional breathlessness",
            ["swelling", "breathlessness on exertion"],
        )
        raise RuntimeError("model stream dropped mid-turn")

    monkeypatch.setattr(runner, "_llm_turn", escalate_then_crash)

    data = await chat(client, RED_FLAG)

    assert data["alert"] is not None
    assert await _alert_count(db_sessionmaker) == 1, "fallback must not duplicate"
    assert await _patient_status(db_sessionmaker) == "alert"


@pytest.mark.anyio
async def test_llm_crash_without_escalation_falls_back(
    client, db_sessionmaker, llm_mode, monkeypatch
):
    async def crash_immediately(tool_context, checklist):
        raise RuntimeError("api unreachable")

    monkeypatch.setattr(runner, "_llm_turn", crash_immediately)

    data = await chat(client, RED_FLAG)

    assert data["alert"] is not None, "fallback classifier must still escalate"
    assert await _alert_count(db_sessionmaker) == 1
    assert await _patient_status(db_sessionmaker) == "alert"


@pytest.mark.anyio
async def test_safety_net_stays_quiet_on_all_clear(
    client, db_sessionmaker, llm_mode, monkeypatch
):
    friendly = "You're doing great, Ahmed — see you tomorrow."

    async def all_clear_llm(tool_context, checklist):
        return friendly, None, "llm"

    monkeypatch.setattr(runner, "_llm_turn", all_clear_llm)

    data = await chat(client, "Feeling good today, took all my medicines")

    assert data["alert"] is None
    assert data["reply"] == friendly, "LLM reply must pass through untouched"
    assert await _alert_count(db_sessionmaker) == 0
