# AfterCare 💙

**AI post-discharge follow-up and escalation agent** — built solo in 48h for the Sofstica SGTDP hackathon (AI Development track).

> When patients go home, nobody follows up — so small problems become expensive, dangerous readmissions. AfterCare checks in with every patient daily over a WhatsApp-style chat, understands how they *feel* in plain language, and the moment it spots a warning sign, it pulls in a human nurse.

## The two screens

| Patient's phone | Nurse's dashboard |
|---|---|
| A warm daily check-in: *"Hi Ahmed 👋 how are you feeling today?"* Free text or one-tap answers. Always calm — never alarming, never diagnostic. | Quiet and green while everyone's fine. The moment a patient reports a red flag, their row jumps to the top, turns red, and shows exactly what they said. |

**The key moment:** a heart-failure patient types *"my ankles are swollen and I get out of breath on the stairs."* The agent replies calmly — *"Thanks for telling me, I'm letting your care team know"* — while the nurse's screen lights up with the matched warning signs and full transcript. Triage, not chatbot.

## Safety is the feature

1. **Never diagnoses, never prescribes.** Its only clinical action is flagging a nurse.
2. **Human always makes the medical decision.**
3. **Escalates when unsure** — tuned to over-flag, never under-flag. A deterministic checklist safety net backs the LLM: if either thinks a message matches a discharge warning sign, a nurse is flagged.
4. **The patient never sees the alarm.** Calm reassurance on their side; the red flag goes to the care team.
5. **No vitals collection** — it asks how patients feel, not for numbers (stays clearly out of medical-device territory).
6. **Synthetic data only.** All patients are fictional.
7. Warning-sign checklists are digitised from standard hospital discharge guidance ("call your doctor if…"), marked as **requiring clinician review** before any real-world use.

## Architecture — "two doors, one brain"

```
Patient (web chat) ─┐
                    ├─► FastAPI agent ──► escalate_to_clinician ──► Nurse dashboard
Patient (WhatsApp) ─┘      │ loads the condition checklist            (red row, reason,
   (bonus channel)         │ OpenAI Agents SDK + clinical tools        transcript)
                           └─► PostgreSQL / SQLite
```

- **Condition-agnostic engine, pluggable checklists.** Heart failure is fully built; post-surgical and COPD are registered stubs. *Adding a disease is a new checklist file, not a new app.*
- **The escalation is a tool call** the model decides to make (`escalate_to_clinician`), backed by a deterministic keyword classifier so the demo works even fully offline.
- The agent remembers prior days' check-ins (`get_patient_history`) — context carries across conversations.

## Stack

Next.js + TypeScript + Tailwind (Vercel) · FastAPI + SQLAlchemy async (Render) · OpenAI Agents SDK (`gpt-5-mini`) · PostgreSQL / SQLite · Twilio WhatsApp sandbox (bonus channel).

## Run it locally

```bash
# backend — http://localhost:8000  (Python 3.14, uv)
cd backend
cp .env.example .env          # add OPENAI_API_KEY, or leave empty for offline mode
uv sync
uv run uvicorn app.main:app --reload

# frontend — http://localhost:3000
cd frontend
npm install
npm run dev
```

Open **/patient** and **/dashboard** side by side. Seeded patients: Ahmed (heart failure), Fatima (post-surgical), Bilal (COPD). No API key? The agent runs on the deterministic checklist classifier — fully functional offline.

```bash
cd backend && uv run pytest   # escalation logic, LLM guardrails, demo-script pins
```

## What's real vs. out of scope

**Real:** the LLM reasoning and free-text understanding, the escalation tooling, the safety net, memory across days, scheduled daily check-ins, both UIs, the tests.
**Out of scope for the MVP:** real patient data (HIPAA), EHR integration, WhatsApp Business API (sandbox only), clinician-reviewed protocol library, scheduling at production scale.

---

*Built with FastAPI, Next.js, and a strong opinion: the AI's job is to notice, a human's job is to decide.*
