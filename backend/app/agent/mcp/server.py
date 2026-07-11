"""Builds the OpenAI Agents SDK agent wired to the five clinical tools.

See tools.py for the note on why the §8 MCP tool surface is exposed as
Agents SDK function tools for the MVP (request-scoped DB session), and
why swapping in a real MCP server later touches only this package.
"""

from __future__ import annotations

from agents import Agent

from app.agent.conditions.base import ConditionChecklist
from app.agent.mcp.tools import (
    ToolContext,
    classify_severity,
    escalate_to_clinician,
    get_condition_checklist,
    get_patient_history,
    log_response,
)
from app.agent.prompts import build_system_prompt
from app.config import get_settings
from app.models import Patient

CLINICAL_TOOLS = [
    get_condition_checklist,
    get_patient_history,
    log_response,
    classify_severity,
    escalate_to_clinician,
]


def build_agent(patient: Patient, checklist: ConditionChecklist) -> Agent[ToolContext]:
    settings = get_settings()
    return Agent[ToolContext](
        name="AfterCare Check-in Agent",
        instructions=build_system_prompt(patient, checklist),
        model=settings.llm_model,
        tools=CLINICAL_TOOLS,
    )
