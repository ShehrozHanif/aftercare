# AfterCare 💙

**An AI agent that checks on patients after they leave the hospital — and calls in a real nurse the moment something looks wrong.**

Built solo in 48 hours for the Sofstica SGTDP hackathon (AI Development track).

---

## The problem, in plain words

When a patient goes home after a hospital stay, almost nobody follows up. Small problems — a bit of swelling, slightly harder breathing — quietly grow at home until the patient collapses and lands back in the emergency room. These readmissions are dangerous for patients and enormously expensive for hospitals. Follow-up calls are proven to prevent them, but hospitals simply don't have enough staff to phone every discharged patient every day.

## Our answer, in one story

Meet **Ahmed, 65**, who just went home after being treated for heart failure.

1. **Every evening his phone buzzes**: *"Hi Ahmed 👋 This is your check-in from City Hospital. Just 2 minutes — how are you feeling today?"*
2. He answers in his own words — *"okay, a bit tired"* — and taps Yes/No buttons for a few quick questions (any swelling? breathing okay? taking your medicines?).
3. **On a good day**, the AI says goodnight and nobody at the hospital lifts a finger. That's the point — no nurse time wasted on healthy patients.
4. **On day 4, Ahmed types**: *"my ankles are swollen and I get out of breath on the stairs."* The AI recognizes that for a heart patient this combination is a warning sign. To Ahmed it stays perfectly calm: *"Thanks for telling me — I'm letting your care team know so someone can check in with you shortly."*
5. **At that same second**, on the nurse's dashboard at the hospital, Ahmed's name jumps to the top and turns red, showing exactly what he reported and his full chat history. A nurse reads it and phones him — **today**, instead of meeting him in the ER next week.

The AI never diagnoses and never treats. Its only job is to **notice** — a human always makes the medical decision.

## What we actually built

| Piece | What it does |
|---|---|
| **Patient chat** (`/patient`) | A warm, WhatsApp-style web chat with big readable text and one-tap answer buttons. Talks to the AI agent. |
| **Nurse dashboard** (`/dashboard`) | A live care-team view. Green rows when everyone's fine; an escalated patient jumps to the top, turns red, and shows the reason, the matched warning signs, the full transcript, and a **"Recent check-ins" history** (was fine Monday, tired Tuesday, swollen today). Refreshes every 3 seconds. |
| **The AI agent** (one shared "brain") | Reads the patient's free-text reply, compares it against that condition's official discharge warning signs, and decides: OK / WARNING / URGENT. Escalation happens by the model calling a real tool (`escalate_to_clinician`) — reasoning + tools + memory, not a scripted bot. |
| **A safety net under the AI** | A deterministic keyword checker runs on every message. If *either* the LLM *or* the checklist thinks something is wrong, a nurse gets flagged. Over-flagging is fine; under-flagging is not. (Bonus: with no API key at all, the whole demo still works offline on this checker.) |
| **Pluggable conditions** | Heart failure is fully built. Post-surgical and COPD are registered stubs. Adding a new disease = adding one checklist file — the engine never changes. |
| **WhatsApp door** (bonus) | The same agent reachable over real WhatsApp via Twilio's sandbox. The channel only changes how messages travel — one brain, two doors. Web chat never depends on it. |
| **Scheduled daily check-ins** (bonus) | A built-in scheduler sends every patient their daily greeting automatically (6 PM PKT by default). `POST /checkins/run` fires the round on demand for the demo. |
| **Tests** | 47 automated tests pin the safety behavior: red-flag messages must always escalate, the scripted all-clear day must never false-alarm, and the demo scripts are locked in as regression tests. |

## The safety rules we never break

1. **Never diagnoses, never prescribes** — it doesn't even name a condition to the patient.
2. **A human always makes the medical decision** — the AI's only clinical action is flagging a nurse.
3. **When unsure, escalate** — a false alarm costs a nurse a glance; a miss can cost a life.
4. **Never alarm the patient** — calm reassurance on their screen; the red flag goes to the care team only.
5. **No vitals collection** — it asks how you *feel*, not for blood-pressure numbers (this deliberately keeps it an early-warning helper, not a regulated medical device).
6. **Synthetic data only** — every patient is fictional.
7. **The medical checklists aren't ours** — they're digitised from the standard "call your doctor if…" discharge sheets hospitals already hand out, and are marked as requiring clinician review before real-world use.

## How it's put together

```
Patient (web chat) ─┐
                    ├─► FastAPI agent ──► escalate_to_clinician ──► Nurse dashboard
Patient (WhatsApp) ─┘      │ loads the condition's checklist         (red row, reason,
                           │ OpenAI Agents SDK + clinical tools       history, transcript)
                           └─► PostgreSQL / SQLite
```

**Stack:** Next.js + TypeScript + Tailwind (frontend) · FastAPI + SQLAlchemy async (backend) · OpenAI Agents SDK with `gpt-5-mini` (the AI) · Twilio WhatsApp sandbox (bonus channel). Deliberately simple — no Kubernetes, no queues; one small app that works.

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

Open **/patient** and **/dashboard** side by side. Seeded patients: Ahmed (heart failure, with two days of check-in history already on file), Fatima (post-surgical), Bilal (COPD). Type Ahmed's day-4 message — *"my ankles are swollen and I get out of breath on the stairs"* — and watch the dashboard.

```bash
cd backend && uv run pytest        # run the 47-test safety suite
curl -X POST localhost:8000/checkins/run   # fire today's check-in round on demand
```

To reset the demo: stop the backend, delete `backend/aftercare.db`, start it again — it reseeds itself.

## Questions people ask

### Why doesn't the "+ Add condition protocol" button do anything?

**It's intentional, not a bug.** The button on the dashboard has no click handler — it's an *affordance*: a visual hint that adding a new disease is a first-class action in this system. Building a real "upload a checklist through the UI" feature would mean a checklist editor, validation, and a clinician-review workflow — days of work for zero demo value, and exactly the kind of thing a real deployment should gate behind clinician review rather than a self-serve button anyway. Today, adding a condition is one Python file in `backend/app/agent/conditions/` (that's the pitch: *"a new checklist, not a new app"*).

The panel next to it shows what's registered:

| Label | Meaning |
|---|---|
| **Heart Failure — Active** | Fully implemented checklist: real symptom questions, real warning signs in three severity tiers (URGENT / WARNING / OK). The demo condition. |
| **Post-surgical — Stub** | Registered with a name and structure, but the clinical checklist isn't filled in yet. |
| **COPD — Stub** | Same — a placeholder proving the slot exists. |

The stubs are shown (not hidden) on purpose: the agent engine is condition-agnostic — it loads whatever checklist matches the patient's condition and runs the identical loop. The stubs are the visual proof that the design scales.

### What are COPD and "post-surgical"?

The other two patient conditions seeded in the demo:

- **COPD — Chronic Obstructive Pulmonary Disease.** A long-term lung disease (usually from smoking) where the airways are permanently narrowed, making breathing hard. It's one of the most common causes of hospital readmission worldwide: patients go home after a flare-up, and catching worsening breathlessness within a day or two can prevent the next emergency admission. Demo patient: **Bilal Khan**.
- **Post-surgical — recovery after an operation.** Not one disease, but the general "you just had surgery, watch for complications" situation: wound infection (redness, swelling, discharge, fever), uncontrolled pain, bleeding. Most complications appear in the first days at home — exactly when nobody is checking on the patient. Demo patient: **Fatima Noor**.

These two were chosen alongside heart failure because they're the classic high-readmission discharge categories every hospital already hands out "call your doctor if…" leaflets for — and together they show the same engine covering a chronic heart disease, a chronic lung disease, and a one-time surgical recovery. (Fatima and Bilal can still chat with the agent — the engine works for them — but with stub checklists they only get the generic safety net, which is why the demo always uses Ahmed.)

## Honest scope

**Real:** the LLM reasoning and free-text understanding, the escalation tooling, the safety net, memory across days, scheduled daily check-ins, both UIs, the tests.
**Out of scope for the MVP:** real patient data (HIPAA), EHR integration, WhatsApp Business API (sandbox only), a clinician-reviewed protocol library, scheduling at production scale.

---

*Built with FastAPI, Next.js, and a strong opinion: the AI's job is to notice, a human's job is to decide.*
