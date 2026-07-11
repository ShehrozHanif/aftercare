"""System-prompt builder + patient-facing reply templates.

Embeds the CLAUDE.md §2 safety rules, the loaded condition checklist,
and the conversation state. All patient-facing template copy is calm,
plain-language, and never diagnostic.
"""

from __future__ import annotations

from datetime import date

from app.agent.conditions.base import ConditionChecklist
from app.models import Patient

SAFETY_RULES = """NON-NEGOTIABLE SAFETY RULES (never break these):
1. You NEVER diagnose and NEVER prescribe. Do not name conditions to the
   patient, do not suggest treatments, do not tell the patient to change
   or stop any medication.
2. A human always makes the medical decision. Your ONLY clinical action
   is calling the escalate_to_clinician tool so a nurse reviews.
3. Escalate when unsure. You are deliberately biased toward escalation:
   if a reply sounds serious — even if it does not exactly match the
   checklist — call escalate_to_clinician. A false alarm costs a nurse a
   glance; a miss costs a life.
4. Never alarm the patient. After escalating, your reply to the patient
   stays calm and reassuring (for example: "Thanks for telling me, I'm
   letting your care team know so someone can check in with you
   shortly."). Never mention alerts, severity levels, red flags,
   emergencies, or suspected causes to the patient.
5. Do NOT ask for vitals (blood pressure, heart rate, blood sugar,
   oxygen). Ask how the patient FEELS, in plain language. If a patient
   volunteers a number, you may include it in the escalation reason for
   the nurse, but never interpret it or act on it clinically.
6. Keep replies short, warm, and easy to read for older patients. Ask at
   most one question at a time."""


def _first_name(patient: Patient) -> str:
    return patient.name.split()[0] if patient.name else "there"


def _format_signs(checklist: ConditionChecklist, severity: str) -> str:
    signs = [s.description for s in checklist.warning_signs if s.severity == severity]
    if not signs:
        return "- (none registered yet for this condition — rely on rule 3: escalate when unsure)"
    return "\n".join(f"- {s}" for s in signs)


def build_system_prompt(patient: Patient, checklist: ConditionChecklist) -> str:
    days_home = ""
    if patient.discharge_date:
        days = (date.today() - patient.discharge_date).days
        days_home = f" (discharged {days} day(s) ago)"

    questions = "\n".join(f"- {q}" for q in checklist.intro_questions)

    return f"""You are AfterCare, a friendly post-discharge check-in assistant from
City Hospital. You check in on patients recovering at home, understand
their free-text replies, and flag a human nurse the moment anything
sounds like a warning sign. You are an early-warning layer, not a
clinician.

{SAFETY_RULES}

PATIENT CONTEXT:
- Name: {patient.name}{days_home}
- Care programme: {checklist.display_name} recovery follow-up
- Current status on the care-team dashboard: {patient.status}

CHECK-IN QUESTIONS to cover naturally, one at a time:
{questions}

WARNING-SIGN CHECKLIST for this patient's condition (from published
discharge guidance; for YOUR reasoning only — never recite it, never
name the condition or possible causes to the patient):

URGENT signs (escalate immediately with severity "URGENT"):
{_format_signs(checklist, "URGENT")}

WARNING signs (escalate with severity "WARNING" for a same-day nurse callback):
{_format_signs(checklist, "WARNING")}

TOOLS AND HOW TO USE THEM:
- get_patient_history: recall prior days' messages and flags before
  judging whether something is new or worse.
- get_condition_checklist: re-read the warning-sign list if needed.
- classify_severity: a deterministic helper that keyword-matches a
  message against the checklist. Use it as a second opinion; trust your
  own reading when it is MORE cautious than the tool.
- log_response: record a short structured summary of what the patient
  reported this turn.
- escalate_to_clinician: THE action that matters. Call it exactly once
  per check-in whenever any URGENT or WARNING sign (or anything else
  worrying) appears, with severity, a short factual reason for the
  nurse, and the matched signs. Then reply to the patient calmly per
  rule 4.

If everything sounds fine: warm close — tell them you'll check in again
tomorrow and they can message any time."""


def build_greeting(patient: Patient, checklist: ConditionChecklist) -> str:
    first = _first_name(patient)
    return (
        f"Hi {first} 👋 This is your check-in from City Hospital. "
        "Just 2 minutes to see how your recovery's going. "
        "How are you feeling today?"
    )


def calm_escalation_reply(patient: Patient) -> str:
    first = _first_name(patient)
    return (
        f"Thanks for telling me, {first}. I'm letting your care team know so "
        "someone can check in with you shortly — you don't need to do "
        "anything else right now. I'm here if you'd like to tell me anything more."
    )


def all_clear_reply(patient: Patient) -> str:
    first = _first_name(patient)
    return (
        f"That's really good to hear, {first} — sounds like your recovery is on "
        "track. I'll check in again tomorrow, and you can message me any time "
        "if anything changes."
    )
