/**
 * Typed mock fixtures matching the CLAUDE.md §8 contract exactly.
 * Used when NEXT_PUBLIC_USE_MOCKS=1 or the backend is unreachable.
 *
 * Covers both demo scenarios (§13):
 *  - Day 1: all-clear check-in (No / No / Yes -> warm close, dashboard stays green)
 *  - Day 4: "ankles swollen" + "out of breath on the stairs" -> WARNING alert,
 *    calm reassurance to the patient, red row on the dashboard.
 */

import type {
  AlertRecord,
  ChatResponse,
  CheckinStartResponse,
  CheckinSummary,
  ConditionProtocol,
  ConversationResponse,
  DashboardStats,
  Message,
  Patient,
  RecoveryReport,
} from "./types";

// ---------------------------------------------------------------------------
// In-memory state (module-scoped, survives navigation within one tab session)
// ---------------------------------------------------------------------------

let nextMessageId = 1;
let nextAlertId = 1;

interface MockPatientState {
  patient: Patient;
  messages: Message[];
  /** index into the scripted check-in question flow */
  step: number;
  conversationId: number;
}

const now = () => new Date().toISOString();

function makePatient(
  id: number,
  name: string,
  condition: string,
  displayName: string,
  dischargeDate: string
): Patient {
  return {
    id,
    name,
    condition,
    condition_display_name: displayName,
    status: "good",
    channel: "web",
    discharge_date: dischargeDate,
    created_at: now(),
    open_alerts: [],
  };
}

const store = new Map<number, MockPatientState>([
  [
    1,
    {
      patient: makePatient(1, "Ahmed Raza", "heart_failure", "Heart Failure", "2026-07-08"),
      messages: [],
      step: 0,
      conversationId: 1,
    },
  ],
  [
    2,
    {
      patient: makePatient(2, "Fatima Noor", "post_surgical", "Post-Surgical Recovery", "2026-07-10"),
      messages: [],
      step: 0,
      conversationId: 2,
    },
  ],
  [
    3,
    {
      patient: makePatient(3, "Bilal Khan", "copd", "COPD", "2026-07-06"),
      messages: [],
      step: 0,
      conversationId: 3,
    },
  ],
]);

function push(state: MockPatientState, sender: "agent" | "patient", text: string): Message {
  const msg: Message = {
    id: nextMessageId++,
    conversation_id: state.conversationId,
    sender,
    text,
    created_at: now(),
  };
  state.messages.push(msg);
  return msg;
}

// ---------------------------------------------------------------------------
// Red-flag detection (mock stand-in for the agent's checklist reasoning).
// Biased toward escalation, per §2 rule 3.
// ---------------------------------------------------------------------------

const URGENT_PATTERNS: Array<[RegExp, string]> = [
  [/chest (pain|pressure|tight)/i, "Chest pain or pressure"],
  [/(faint|fainted|passing out|blacked out)/i, "Fainting or near-fainting"],
  [/(can'?t breathe|breathless at rest|severe.*breath)/i, "Severe or sudden shortness of breath"],
  [/confus/i, "New confusion"],
];

const WARNING_PATTERNS: Array<[RegExp, string]> = [
  [/(swollen|swelling|puffy)/i, "New or increased swelling in legs, ankles, feet, or abdomen"],
  [
    /(out of breath|short(ness)? of breath|breathless|hard to breathe|wheez)/i,
    "Increasing shortness of breath on exertion, or breathless lying flat / needing more pillows",
  ],
  [/(gained.*(weight|kg|lb)|weight.*(gain|up))/i, "Sudden weight gain"],
  [/(worse|worsening).*(cough)|cough.*(worse|worsening)|new cough/i, "New or worsening cough or wheezing"],
  [/(exhausted|so tired|very tired|fatigue|no energy)/i, "Increasing fatigue / can't do usual activities"],
  [
    /(ran out|stopped taking|haven'?t (been )?tak|missed.*(dose|medicine|medication)|side effect)/i,
    "Not taking medication",
  ],
];

function matchSigns(text: string): { severity: "WARNING" | "URGENT"; signs: string[] } | null {
  const urgent = URGENT_PATTERNS.filter(([re]) => re.test(text)).map(([, s]) => s);
  if (urgent.length > 0) return { severity: "URGENT", signs: urgent };
  const warning = WARNING_PATTERNS.filter(([re]) => re.test(text)).map(([, s]) => s);
  if (warning.length > 0) return { severity: "WARNING", signs: warning };
  return null;
}

// Calm reassurance template (§2 rule 4 — never alarming, never diagnostic).
function calmEscalationReply(name: string): string {
  const first = name.split(" ")[0];
  return `Thanks for telling me, ${first}. I'm letting your care team know so someone can check in with you shortly — you don't need to do anything else right now. I'm here if you'd like to tell me anything more.`;
}

// Scripted all-clear question flow (§5): open question -> symptoms -> meds -> close.
const FLOW: string[] = [
  "Any new swelling in your legs, ankles or feet?",
  "How is your breathing — any harder than usual, or when lying flat?",
  "Are you managing to take your medicines as prescribed?",
  "That all sounds good — you're doing really well. I'll check in again tomorrow, and you can message me here any time if anything changes. Take care!",
];

// ---------------------------------------------------------------------------
// Mock API surface (same signatures/shapes as the real client)
// ---------------------------------------------------------------------------

function getState(patientId: number): MockPatientState {
  const state = store.get(patientId);
  if (!state) throw new Error(`Mock: unknown patient ${patientId}`);
  return state;
}

export function mockGetPatients(): Patient[] {
  // Return deep-ish copies so React state diffs correctly.
  return Array.from(store.values()).map(({ patient }) => ({
    ...patient,
    open_alerts: [...(patient.open_alerts ?? [])],
  }));
}

export function mockGetConditions(): ConditionProtocol[] {
  return [
    {
      name: "heart_failure",
      display_name: "Heart Failure",
      implemented: true,
      intro_questions: [
        "How are you feeling today, in your own words?",
        "Any new swelling in your legs, ankles, feet, or tummy?",
        "How is your breathing — any more breathless than usual?",
        "Are you managing to take your medicines as usual?",
      ],
      signs: {
        urgent: [
          "Chest pain or pressure",
          "Severe or sudden shortness of breath / breathless at rest",
          "Fainting or near-fainting",
          "Very fast or irregular heartbeat with dizziness",
          "New confusion",
        ],
        warning: [
          "New or increased swelling in legs, ankles, feet, or abdomen",
          "Sudden weight gain",
          "Increasing shortness of breath on exertion, or breathless lying flat",
          "New or worsening cough or wheezing",
          "Increasing fatigue / can't do usual activities",
          "Not taking medication (ran out, forgot, or stopped)",
        ],
      },
    },
    {
      name: "post_surgical",
      display_name: "Post-Surgical Recovery",
      implemented: true,
      intro_questions: [
        "How are you feeling today, in your own words?",
        "How is the wound or the area around your operation looking and feeling?",
        "Any fever, or redness, swelling, or fluid coming from the wound?",
        "Are you managing to take your medicines as usual?",
      ],
      signs: {
        urgent: [
          "Heavy or uncontrolled bleeding from the wound",
          "The wound has opened up (dehiscence)",
          "Sudden breathlessness, chest pain, or a hot swollen painful calf",
          "High fever with feeling very unwell (possible serious infection)",
        ],
        warning: [
          "Signs of wound infection — spreading redness, warmth, swelling, or discharge",
          "Fever or raised temperature",
          "Pain getting worse instead of better",
          "Ongoing vomiting or unable to keep fluids down",
          "Not taking medication (ran out, forgot, or stopped)",
        ],
      },
    },
    {
      name: "copd",
      display_name: "COPD",
      implemented: true,
      intro_questions: [
        "How are you feeling today, in your own words?",
        "How is your breathing compared with a normal day for you?",
        "Any change in your cough or the phlegm you're bringing up?",
        "Are you managing to take your medicines and inhalers as usual?",
      ],
      signs: {
        urgent: [
          "Severe breathlessness — breathless at rest or can't finish a sentence",
          "Blue lips or fingertips",
          "New confusion or unusual drowsiness",
          "Coughing up blood",
          "Chest pain",
        ],
        warning: [
          "More short of breath than usual, or breathless doing less",
          "More phlegm than usual, or a changed colour (yellow/green/brown)",
          "Coughing more than usual",
          "More wheezing or chest tightness",
          "Fever or signs of a chest infection",
          "Not taking medicines or inhalers as usual",
        ],
      },
    },
  ];
}

export function mockGetStats(): DashboardStats {
  const patients = Array.from(store.values());
  const needs_call = patients.filter((s) =>
    (s.patient.open_alerts ?? []).some((a) => a.status === "open")
  ).length;
  return {
    patients_monitored: patients.length,
    needs_call,
    checkins_today: patients.length, // one scripted check-in each in mock mode
  };
}

export function mockGetConversation(patientId: number): ConversationResponse {
  const state = getState(patientId);
  return {
    patient_id: patientId,
    patient_name: state.patient.name,
    messages: [...state.messages],
  };
}

export function mockStartCheckin(patientId: number): CheckinStartResponse {
  const state = getState(patientId);
  const first = state.patient.name.split(" ")[0];
  state.step = 0;
  const reply = `Hi ${first} 👋 This is your check-in from City Hospital. Just 2 minutes to see how your recovery's going. How are you feeling today?`;
  push(state, "agent", reply);
  return { conversation_id: state.conversationId, reply };
}

export function mockChat(patientId: number, message: string): ChatResponse {
  const state = getState(patientId);
  push(state, "patient", message);

  const match = matchSigns(message);
  if (match) {
    const alert: AlertRecord = {
      id: nextAlertId++,
      patient_id: patientId,
      conversation_id: state.conversationId,
      severity: match.severity,
      reason: `Patient message matched discharge warning signs: ${match.signs.join(
        "; "
      )}. Patient said: "${message}"`,
      matched_signs: match.signs,
      status: "open",
      created_at: now(),
    };
    state.patient.open_alerts = [...(state.patient.open_alerts ?? []), alert];
    state.patient.status = "alert";
    const reply = calmEscalationReply(state.patient.name);
    push(state, "agent", reply);
    return { reply, alert };
  }

  const reply =
    state.step < FLOW.length ? FLOW[state.step] : "Thanks for the update — noted for your care team. Anything else you'd like to mention?";
  state.step += 1;
  push(state, "agent", reply);
  return { reply, alert: null };
}

export function mockGetCheckins(patientId: number): CheckinSummary[] {
  const state = getState(patientId);
  const dayMs = 24 * 60 * 60 * 1000;
  // Fixed illustrative history (newest first) + today's live state.
  const history: CheckinSummary[] = [
    {
      conversation_id: state.conversationId,
      started_at: now(),
      escalated: (state.patient.open_alerts ?? []).length > 0,
      severity: state.patient.open_alerts?.[0]?.severity ?? null,
      summary:
        state.patient.open_alerts?.[0]?.reason ??
        "Feeling okay, taking medicines",
    },
    {
      conversation_id: state.conversationId - 1,
      started_at: new Date(Date.now() - dayMs).toISOString(),
      escalated: false,
      severity: null,
      summary: "A little tired, otherwise well",
    },
    {
      conversation_id: state.conversationId - 2,
      started_at: new Date(Date.now() - 2 * dayMs).toISOString(),
      escalated: false,
      severity: null,
      summary: "Feeling stable, no new symptoms",
    },
  ];
  return history;
}

export function mockGetReport(patientId: number): RecoveryReport {
  const state = getState(patientId);
  const alerts = state.patient.open_alerts ?? [];
  return {
    patient_id: patientId,
    patient_name: state.patient.name,
    condition_display_name:
      state.patient.condition_display_name ?? state.patient.condition,
    discharge_date: state.patient.discharge_date ?? null,
    days_since_discharge: 4,
    status: state.patient.status,
    checkins_sent: 3,
    checkins_answered: 3,
    medication_concerns: 0,
    symptom_mentions: alerts.map((a) => ({
      date: a.created_at,
      severity: a.severity,
      signs: a.matched_signs,
    })),
    alerts_total: alerts.length,
    alerts_open: alerts.filter((a) => a.status === "open").length,
    generated_at: now(),
  };
}

export function mockResolvePatient(patientId: number): Patient {
  const state = getState(patientId);
  if ((state.patient.open_alerts ?? []).some((a) => a.status === "open")) {
    throw new Error("Open alerts must be acknowledged before resolving");
  }
  state.patient.status = "good";
  state.patient.open_alerts = [];
  return { ...state.patient };
}

export function mockAckAlert(alertId: number): AlertRecord {
  for (const state of store.values()) {
    const alerts = state.patient.open_alerts ?? [];
    const found = alerts.find((a) => a.id === alertId);
    if (found) {
      found.status = "acknowledged";
      state.patient.open_alerts = alerts.filter((a) => a.id !== alertId);
      if ((state.patient.open_alerts ?? []).length === 0) {
        state.patient.status = "watch"; // acknowledged, nurse keeping an eye
      }
      return { ...found };
    }
  }
  throw new Error(`Mock: unknown alert ${alertId}`);
}
