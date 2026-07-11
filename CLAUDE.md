# CLAUDE.md — AfterCare

> Project context and build instructions for Claude Code.
> Read this whole file before writing any code. It defines what we are building, the rules that must never be broken, the exact stack, and the execution order.

---

## 1. What this project is

**AfterCare** is an AI post-discharge follow-up and escalation agent.

When a patient leaves the hospital, follow-up mostly doesn't happen — and small problems at home turn into expensive, dangerous readmissions. AfterCare is a friendly daily check-in (over a WhatsApp-style chat) that asks the patient how they feel in plain language, understands their free-text replies, remembers their history, and **the moment it detects a warning sign, it flags a human nurse** on a care-team dashboard. It never diagnoses and never prescribes — it is an early-warning/triage layer with a human always in the loop.

**One-line pitch:** "When patients go home, nobody follows up — so they get worse and land back in hospital. AfterCare watches over every patient and pulls in a nurse the moment something's wrong."

**Context for this build:** This is being built for the **Sofstica SGTDP hackathon** (AI Development track, solo, 48 hours). It is a demo-grade MVP, not a production clinical system. The goal is a working, deployed prototype with a demo that shows the agent catching a red flag live.

---

## 1.5 Current repo state & commands

**Status: Phases 0–3 are COMPLETE and verified end-to-end.** Done: agent backend (escalation + safety net + tests), patient chat, live nurse dashboard, README, recent check-ins history panel, scripted seed history (Ahmed Day-1/Day-2 all-clear + Fatima post-op), daily conversation rollover. Beyond the original spec: `GET /patients/{id}/checkins` (nurse-facing history, in §8).

**▶ RESUME HERE — remaining work, in order:**
1. **Deploy** (the original goal is a *deployed* prototype): backend + Postgres on Render, frontend on Vercel, set `NEXT_PUBLIC_API_URL` / `FRONTEND_URL` / `OPENAI_API_KEY` / `DATABASE_URL`. Needs the user's Render/Vercel accounts — ask them to log in / authorize.
2. **Phase 4 (bonus): Twilio WhatsApp sandbox** — `POST /whatsapp/incoming` + `services/twilio_client.py` per §8. Needs the user's Twilio credentials.
3. **Phase 5 (bonus): scheduled daily check-ins** — otherwise a talk-track point.
4. Before the demo: delete `backend/aftercare.db` and restart to reseed the clean state; run the §13 script once as rehearsal. `jounry.md` is the original design journal; it contains the full rationale behind the safety rules and the no-vitals / no-training decisions — read it if a design choice here seems arbitrary.

Hard-won implementation notes:
- The Agents SDK reads `OPENAI_API_KEY` from the process env; the app loads `.env` via pydantic-settings, so `main.py` hands the key over with `set_default_openai_key()` at startup.
- All five clinical tools share one request-scoped AsyncSession — **parallel tool calls corrupt it** (duplicate alert INSERTs, lost status updates). `build_agent` sets `parallel_tool_calls=False`; keep it that way.
- `agent_turn` has a deterministic safety net: if the LLM path returns without escalating a message the checklist matches, the keyword classifier escalates anyway (§2 rule 3). With no `OPENAI_API_KEY`, the whole agent runs on that classifier — the demo works offline.
- **Because the safety net runs on every turn, checklist keywords must never match normal-recovery phrases.** Bare "tired" once flagged the scripted Day-1 all-clear line as WARNING (dashboard went red on the normal-path demo). Signs describing *progression* need qualified keywords ("more tired", not "tired"). `tests/test_matcher.py` pins the Day-1 and Day-4 demo scripts — run it after any keyword change.
- Negation detection (`conditions/base.py`) matches whole words only; "can't"/"cannot" are deliberately never denials ("cannot do my shopping" affirms the fatigue sign).
- SQLite drops tzinfo on read, so schema datetimes use `schemas.UTCDateTime`, which re-stamps UTC and serializes with a `Z` — otherwise browsers parse timestamps as local time (5h off in Karachi). Use it for any new datetime field.
- Local dev DB is SQLite (`backend/aftercare.db`); delete the file and restart to reseed a clean demo state.
- Test suite lives in `backend/tests/` (escalation logic, LLM guardrails, matcher demo-script pins, routes). `uv run pytest` from `backend/` — must stay green.

**Package management is [uv](https://docs.astral.sh/uv/), not pip.** Python 3.14 is pinned via `backend/.python-version`.

Dev commands:
- Backend: `uv run uvicorn app.main:app --reload` (from `backend/`; `uv add <pkg>` / `uv sync` for deps)
- Frontend: `npm run dev` (from `frontend/`)
- Tests: `uv run pytest` (from `backend/`)

---

## 2. NON-NEGOTIABLE SAFETY RULES (never break these)

These are the most important rules in the project. They are both an ethical requirement and the core of the pitch ("safety is a feature").

1. **The agent NEVER diagnoses and NEVER prescribes.** It does not name conditions to the patient, does not suggest treatments, does not tell a patient to change medication.
2. **Human always makes the medical decision.** The agent's only clinical action is to *flag* a nurse. A human reviews and decides.
3. **Escalate when unsure.** The agent is deliberately biased toward escalation. If a reply sounds serious — even if it doesn't exactly match the checklist — flag a human. A false alarm costs a nurse a glance; a miss costs a life. Tune for over-flagging, never under-flagging.
4. **Never alarm the patient.** On a red flag, the patient-facing message stays calm and reassuring ("Thanks for telling me, I'm letting your care team know so someone can check in with you shortly"). The alarm goes to the nurse screen, not the patient.
5. **No vitals collection as the core flow.** The agent asks how the patient *feels* (symptoms, plain language), not "enter your blood pressure/heart rate/sugar." Collecting and reacting to numeric vitals pushes us toward regulated medical-device territory — stay out of it. (Exception: if a patient volunteers a reading, the agent may pass it to the nurse, but never demands one and never acts on it clinically.)
6. **Synthetic data only.** No real patient data, ever. All demo patients are fictional. Real patient data (HIPAA/health-privacy law) is explicitly out of scope for the MVP.
7. **Clinical logic comes from published discharge guidelines, not invented by us.** The warning-sign checklists are digitised versions of standard hospital discharge "call your doctor if…" guidance, and are marked as requiring clinician review before any real-world use.

---

## 3. Architecture — "two doors, one brain"

```
   Patient (web chat UI)  ─┐
                           ├─►  FastAPI agent (ONE shared brain)  ─►  Escalation  ─►  Nurse Dashboard
   Patient (WhatsApp) ─────┘        │  loads condition checklist
     via Twilio webhook             │  calls LLM + MCP tools
                                     │  decides: OK / WARNING / URGENT
                                     └─►  persists to PostgreSQL
```

- **Two input channels** (web chat + WhatsApp) feed the **same** agent service. Do not build two agents. The channel only changes how a message arrives and how the reply is sent back.
- The **agent** is condition-agnostic. It loads a **checklist** for the patient's condition and runs the same loop regardless of condition.
- **Escalation is an MCP tool call** (`escalate_to_clinician`) — the model decides to call it. This is what makes the system genuinely agentic (reasoning + tool use + memory), not a scripted chatbot.
- The **nurse dashboard** reads patient status + alerts. It does not care which channel the patient used.

---

## 4. Tech stack (deliberately boring for a 48h MVP)

| Layer | Choice | Deploy |
|---|---|---|
| Frontend | Next.js + React + TypeScript + Tailwind CSS | **Vercel** |
| Backend | **FastAPI** (Python) | **Render** |
| Database | PostgreSQL (Render managed) | Render |
| AI / agent | **OpenAI LLM** (we use OpenAI API keys) + **OpenAI Agents SDK** + **custom MCP server** for clinical tools | — |
| Messaging | Web chat (primary, always works) + **Twilio WhatsApp Sandbox** (bonus, real WhatsApp for demo) | — |

### Stack rules
- **DO NOT use Kubernetes, Kafka, or Dapr for this MVP.** We have one small app. K8s here is over-engineering and a sharp judge marks it down. Vercel + Render is correct: zero DevOps, deploys in minutes. (K8s/scale is a *"phase two"* talking point only — see §12.)
- **WhatsApp is a bonus layer, never a dependency.** Build and nail the web-chat demo FIRST — it is the guaranteed, offline-proof demo. Only add Twilio once the core works and there are hours to spare. The demo must be able to run fully on web chat alone if WhatsApp/wifi fails on stage.
- Reuse Shehroz's existing patterns: FastAPI + async + SQLAlchemy + Pydantic + pytest; Next.js/Tailwind frontend.
- **Python 3.14 is pinned** (`.python-version` + `requires-python`). If any dependency (asyncpg, OpenAI Agents SDK, etc.) fails to install on 3.14, relax both to 3.12/3.13 immediately rather than fighting compatibility during the 48h.

---

## 5. The patient conversation flow

Keep it to ~2 minutes, plain language, tappable answers where possible. The agent tailors the symptom questions to the patient's condition (via the loaded checklist).

1. **Greeting + orientation** — warm, names the hospital, sets time expectation.
   > "Hi Ahmed 👋 This is your check-in from City Hospital. Just 2 minutes to see how your recovery's going. How are you feeling today?"
2. **One open question first** — let them answer freely ("how are you feeling?"). This is where the LLM edge shows (understands free text).
3. **3–5 condition-specific symptom questions** — plain language, ideally Yes / No / A little. (For heart failure: swelling, breathlessness, etc. — see §7.)
4. **Medication check** — "Are you managing to take your medicines?" If no, softly ask why (forgot / side effects / ran out).
5. **Branch (the key moment):**
   - **All clear →** warm close, "I'll check in again tomorrow, message me any time."
   - **Warning/Urgent →** calm reassurance to the patient + `escalate_to_clinician` fires → nurse dashboard lights up.
6. **Always-open door** — patient can message any time (e.g. "feeling worse tonight"), which re-runs the check for red flags.

---

## 6. Pluggable condition architecture (IMPORTANT — build for this from day one)

Each medical condition is a **self-contained checklist module**. The agent engine never changes; only the checklist swaps based on `patient.condition`.

- For the hackathon: **Heart Failure is fully built.** That is the demo condition.
- Other conditions (Post-surgical, COPD, Liver transplant, etc.) are **registered stubs** so the design visibly scales. The nurse dashboard shows a condition tag on every patient and an "Add condition protocol" affordance.
- Adding a condition later = adding one checklist file to the registry. No engine changes. This is a core pitch point: "adding a disease is a new checklist, not a new app."

Implement checklists as a registry:

```
agent/conditions/
  __init__.py          # CONDITIONS registry: name -> checklist object
  heart_failure.py     # fully implemented
  post_surgical.py     # stub (structure only)
  copd.py              # stub
```

Each checklist object provides: `display_name`, `intro_questions` (the symptom questions to ask), and `warning_signs` (structured signs with severity), consumed by the system-prompt builder.

---

## 7. Heart Failure checklist (the demo condition)

> Source: standard heart-failure discharge warning-sign guidance (the "call your doctor / call 911 if…" instructions hospitals give HF patients). **Requires clinician review before real-world use.** Encode as three severity tiers.

**URGENT** (escalate immediately; nurse contacts now / advise emergency care):
- Chest pain or pressure
- Severe or sudden shortness of breath / breathless at rest
- Fainting or near-fainting
- Very fast or irregular heartbeat with dizziness
- New confusion

**WARNING** (flag nurse for same-day callback):
- New or increased swelling in legs, ankles, feet, or abdomen
- Sudden weight gain (~2–3 lb / ~1–1.5 kg in a day, or ~5 lb / ~2.3 kg in a week)
- Increasing shortness of breath on exertion, or breathless lying flat / needing more pillows
- New or worsening cough or wheezing
- Increasing fatigue / can't do usual activities
- Not taking medication (ran out, forgot, or stopped due to side effects)

**OK** (routine, continue monitoring):
- Feeling stable, no new symptoms, taking medicines

Symptom questions to ask this patient: how they feel (open), leg/ankle swelling, breathing/breathlessness, medication adherence.

Demo trigger: patient reports **new ankle swelling + breathlessness on exertion** → WARNING → escalate.

---

## 8. Backend spec (FastAPI)

### Data model (SQLAlchemy)
- **conditions**: `id, name, display_name` (checklist logic lives in code registry, keyed by name)
- **patients**: `id, name, condition (fk name), discharge_date, phone (nullable), channel ('web'|'whatsapp'), status ('good'|'watch'|'alert'), created_at`
- **conversations**: `id, patient_id, started_at`
- **messages**: `id, conversation_id, sender ('agent'|'patient'), text, created_at, meta (JSON)`
- **alerts**: `id, patient_id, conversation_id, severity ('WARNING'|'URGENT'), reason, matched_signs (JSON), status ('open'|'acknowledged'|'resolved'), created_at`

### Core service — `agent/runner.py`
`async def agent_turn(patient, incoming_text) -> {reply, alert?}`:
1. Load the condition checklist for `patient.condition`.
2. Build the system prompt (safety rules + checklist + conversation state) via `agent/prompts.py`.
3. Call the LLM with conversation history + the new patient message, using the OpenAI Agents SDK with the MCP tools available.
4. The model produces a patient-facing reply and, if it detects a warning/urgent sign, **calls the `escalate_to_clinician` MCP tool** with `{severity, reason, matched_signs}`.
5. If escalated: create an `alert`, set `patient.status = 'alert'`, and ensure the patient-facing reply uses the calm reassurance template (never alarming, never diagnostic).
6. Persist patient + agent messages.
7. If channel is WhatsApp, send the reply via Twilio; if web, return it in the HTTP response.

### MCP server — `agent/mcp/`
Exposes the clinical tools the model can call (this is the differentiator — real, load-bearing MCP):
- `get_condition_checklist(condition)` → the warning-sign list for the patient's condition
- `get_patient_history(patient_id)` → prior messages/flags (memory across days)
- `log_response(patient_id, text)` → persist a structured response
- `classify_severity(text, condition)` → helper the model can use (OK/WARNING/URGENT)
- `escalate_to_clinician(patient_id, severity, reason, matched_signs)` → creates the alert + updates status (**the money action**)

### Routes
- `POST /chat` — body `{patient_id, message}` → runs `agent_turn`, returns `{reply, alert?}`. **(web chat door)**
- `POST /whatsapp/incoming` — Twilio webhook (form-encoded `From`, `Body`); map `From` number → patient; run `agent_turn`; reply via Twilio. **(WhatsApp door)**
- `POST /checkins/{patient_id}/start` — agent sends the first greeting (for a manual/scheduled check-in trigger in the demo)
- `GET /patients` — dashboard list with current status + condition tag
- `GET /patients/{id}/conversation` — full transcript (for "View conversation")
- `GET /patients/{id}/checkins` — recent check-in history: one summary row per conversation `{conversation_id, started_at, escalated, severity, summary}` (nurse "memory across days" panel)
- `POST /alerts/{id}/ack` — nurse acknowledges an alert

### Twilio (bonus) — `services/twilio_client.py`
- Uses Twilio **WhatsApp Sandbox** (no business verification, works in ~1 hour, for demo phones that have joined the sandbox).
- `send_whatsapp(to, body)` wraps the Twilio REST client.
- The `/whatsapp/incoming` webhook and `send_whatsapp` are the only WhatsApp-specific code; the agent is untouched.
- **Fallback rule:** if Twilio is unavailable, the web chat path must still work end-to-end.

---

## 9. Frontend spec (Next.js)

### Use the installed design skills for all UI work

The **ui-ux-pro-max** skill suite is installed in `.claude/skills/` — invoke these skills when building or reviewing any frontend code, don't design from scratch:

- **`ui-ux-pro-max`** — the main one. Use it when planning/building/reviewing any page or component (patient chat, nurse dashboard): styles, color palettes, typography, layout, accessibility, animation. It has a searchable local database (`python .claude/skills/ui-ux-pro-max/scripts/search.py "<query>"`).
- **`ui-styling`** — when implementing with Tailwind / shadcn/ui components (dialogs, forms, tables, status pills), theming, and responsive layouts.
- **`design-system`** — when setting up the design tokens (§ tokens below) as CSS variables with a primitive→semantic→component structure.
- The others (`design`, `brand`, `slides`, `banner-design`) are for pitch assets — logo, deck, banners — not the app itself.

### 21st.dev CLI (component search — free quota only)

The `21st` CLI is installed globally and logged in (account `shehrozhanif54`, **free tier**). It can pull ready-made React/Tailwind components.

- **Hard rule: stay within the free quota. Never exceed it, never suggest upgrading.** The free tier allows **2 component-code retrievals per day** (`21st get <id>` / `21st add`). Check remaining quota with `21st usage` BEFORE any retrieval; if 0 remain, do NOT use 21st.dev at all for code — build the component by hand with the skills above instead.
- Unlimited (free) commands: `21st search "<query>"` to browse, `21st logo <query>` for brand SVG logos.
- Spend the 2 daily retrievals deliberately on high-value pieces (e.g. a dashboard shell or chat UI), not on trivial components like buttons.
- Never buy paid templates/components (prices show in search results, e.g. `[template $39]`).

A static HTML prototype (`AfterCare_prototype.html`) is the visual reference — **note: it is not in the repo yet.** Until it's added, treat the design tokens below as the source of truth. Two routes:

- **`/patient`** — WhatsApp-style chat. Calm, warm palette (healthcare teal + soft off-white), large readable text (older users), tappable answer chips (Yes / No / A little), typing indicator. Talks to `POST /chat`.
- **`/dashboard`** — nurse care-team view. Crisp, professional, information-dense. Patient list with **condition tag** + status pill (green "All good" / amber "Watch" / red "Needs call"). Escalated patients jump to top, turn red, show reason + "View conversation" transcript. Polls `GET /patients` (or websocket if time) so an escalation appears live. An "Add condition protocol" affordance signals the pluggable design.

Design tokens (from the prototype): pine `#1E5A4F`, page `#E9F0ED`, good `#2E9A6C`, watch `#C98A2B`, alert `#CE5656`, ink `#15302A`. Patient side warm/rounded; dashboard side clean/precise. Respect reduced-motion; visible keyboard focus.

---

## 10. Repo structure

Rooted at the actual repo root (`healthcare_mvp/`), not a nested `aftercare/` folder:

```
healthcare_mvp/            # repo root
  backend/
    app/
      main.py
      config.py
      db.py
      models.py
      schemas.py
      seed.py                 # synthetic patients (Ahmed = heart failure demo)
      routers/
        chat.py
        whatsapp.py
        patients.py
        alerts.py
      agent/
        runner.py             # agent_turn orchestration
        prompts.py            # system-prompt builder (safety + checklist)
        conditions/
          __init__.py         # CONDITIONS registry
          heart_failure.py    # full
          post_surgical.py    # stub
          copd.py             # stub
        mcp/
          server.py           # MCP server
          tools.py            # tool implementations
      services/
        twilio_client.py
    tests/                    # pytest — agent decisions, escalation logic
    pyproject.toml            # uv-managed dependencies (no requirements.txt)
    .env.example
  frontend/
    app/
      patient/page.tsx
      dashboard/page.tsx
    components/
    lib/api.ts
  jounry.md                   # design journal (product rationale)
  README.md
```

Render deploys uv projects natively (`uv sync` in build, `uv run uvicorn ...` as start command); if a `requirements.txt` is ever needed, export it with `uv export --format requirements-txt` rather than maintaining one by hand.

---

## 11. Build order (execution plan — demo-first)

### Sub-agent workflow

Two custom sub-agents are defined in `.claude/agents/` — use them to parallelize the build:

- **`backend-dev`** — owns everything under `backend/` (agent loop, checklists, MCP tools, routers, models, tests). Never touches `frontend/`.
- **`frontend-dev`** — owns everything under `frontend/` (patient chat, nurse dashboard, API client, tokens). Never touches `backend/`. Builds against the §8 API contract, with typed mocks if the backend isn't ready.
- **Main session = orchestrator.** It does Phase 0 (scaffold, contract), dispatches both agents in parallel, then owns integration, end-to-end verification, and demo polish. Never delegate integration.
- **CLAUDE.md §8 is the frozen API contract** between the two. Any contract change goes through the orchestrator and updates §8 first.

**Do these in order. Each phase must leave a working, demoable state before moving on.**

- **Phase 0 — Scaffold (do before the hackathon if possible):** repo skeleton, FastAPI "hello", Next.js skeleton, DB models + migrations, deploy pipeline to Render + Vercel wired and green. Goal: start the 48h at hour zero, not on boilerplate.
- **Phase 1 — Core agent + web chat (the guaranteed demo):** `agent_turn`, heart-failure checklist, system prompt, LLM call, `escalate_to_clinician` MCP tool, `POST /chat`, patient chat UI. End state: you can chat as a patient and trigger an escalation.
- **Phase 2 — Nurse dashboard + escalation surfacing:** `GET /patients`, `GET /patients/{id}/conversation`, dashboard UI with live status + red-flag row + transcript. End state: the two-screen "red flag lights up" demo works.
- **Phase 3 — Demo polish + seed data:** synthetic patients, the two scripted scenarios (Day 1 all-clear, Day 4 escalation), copy pass, reduced-motion, mobile. End state: a clean, reliable stage demo.
- **Phase 4 — BONUS, only if time: Twilio WhatsApp sandbox.** `POST /whatsapp/incoming` + `send_whatsapp`. End state: a real WhatsApp message on your own phone, with web-chat fallback intact.
- **Phase 5 — BONUS: scheduled daily check-ins** (a simple scheduler that fires the greeting). Talk-track otherwise.

**Rule:** never let a bonus phase eat time the core phases need. A smaller thing that works flawlessly beats an ambitious thing that breaks. Non-functional = disqualified.

---

## 12. What's real vs faked (be honest about this in the demo)

- **Real:** the agent/LLM reasoning, the free-text understanding, the escalation logic, the MCP tools, the dashboard, the web chat, the deployment.
- **Real if Phase 4 done:** WhatsApp via Twilio sandbox (for phones that joined the sandbox).
- **Faked / out of scope for MVP:** real WhatsApp Business API (needs Meta verification — days), EHR integration (Epic/Cerner), HIPAA-grade compliance infra, real patient data, clinician-reviewed protocols at scale, scheduled check-ins at production scale.
- **"Phase two" talking points (say, don't build):** real WhatsApp Business API; Kubernetes + Kafka/Dapr for many concurrent patients and background check-in jobs (this is where Shehroz's LearnFlow experience becomes the honest scale answer); HIPAA infra + audit logging; EHR write-back; a clinician-reviewed library of condition checklists.

---

## 13. Demo script (the winning moment)

1. Open both screens side by side (patient phone + nurse dashboard).
2. Play **Day 1**: patient answers "No / No / Yes" → warm all-clear close. Dashboard stays calm green. (Shows the normal path.)
3. Play **Day 4**: patient reports "ankles are swollen" + "out of breath on the stairs." → agent stays calm and reassuring to the patient, **and Ahmed's row jumps to the top of the nurse dashboard and turns red**, with the reason + transcript. (The triage-not-chatbot moment.)
4. One line: "It never diagnoses — it notices a red flag and gets a human involved faster. Adding another disease is a new checklist, not a new app."

---

## 14. Positioning (for the pitch / judge questions)

- **Problem:** ~half of readmitted patients had no follow-up visit; preventable readmissions cost the US ~$41B/year and trigger CMS penalties. Follow-up demonstrably reduces readmissions but hospitals can't staff it at scale.
- **Why us vs incumbents (Hippocratic AI, CipherHealth, Cadence, etc.):** they chase large US hospitals with heavy EHR integrations. Our wedge is the segment they ignore — **WhatsApp-first follow-up for smaller clinics and emerging markets (Pakistan/South Asia)**, lightweight, switch-on-tomorrow. The LLM is not the moat; focus, workflow fit, and channel are.
- **Business model:** B2B SaaS, monthly subscription to clinics/hospitals; one prevented readmission > monthly fee; later per-patient or outcome-based pricing.
- **Safety as a feature:** never diagnoses, human-in-the-loop, escalates when unsure.

---

## 15. Environment variables (`.env.example`)

```
# LLM — we use OpenAI keys (pairs with the OpenAI Agents SDK)
OPENAI_API_KEY=
LLM_MODEL=gpt-5-mini            # cost-aware default for the MVP; gpt-5 if quality issues show up in agent decisions

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/aftercare

# Twilio (bonus — WhatsApp sandbox)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   # Twilio sandbox number

# App
FRONTEND_URL=https://aftercare.vercel.app
```

---

## 16. Coding conventions

- Python: FastAPI + async, SQLAlchemy 2.x, Pydantic v2, type hints, `pytest` for the agent decision/escalation logic (test that red-flag inputs escalate and clear inputs don't).
- Keep the agent channel-agnostic: `agent_turn` must not know or care whether the message came from web or WhatsApp.
- Keep clinical logic in the checklist modules, not scattered in the agent — so a new condition never touches the engine.
- Never hardcode a diagnosis or treatment string anywhere. The agent flags; it does not advise.
- Commit small; keep the repo public and clean (it's part of the hackathon submission and judged).
