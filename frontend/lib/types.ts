/**
 * Shared types matching the frozen API contract in CLAUDE.md §8,
 * verified against the running backend (2026-07-12). Do NOT invent new
 * shapes here — any contract change goes through the orchestrator and
 * updates §8 first.
 */

export type PatientStatus = "good" | "watch" | "alert";
export type AlertSeverity = "WARNING" | "URGENT";
export type AlertStatus = "open" | "acknowledged" | "resolved";
export type Channel = "web" | "whatsapp";
export type Sender = "agent" | "patient";

export interface AlertRecord {
  id: number;
  patient_id: number;
  conversation_id?: number | null;
  severity: AlertSeverity;
  reason: string;
  matched_signs: string[];
  status: AlertStatus;
  created_at: string; // ISO timestamp
}

export interface Patient {
  id: number;
  name: string;
  /** condition registry key, e.g. "heart_failure" */
  condition: string;
  /** human label from the backend, e.g. "Heart Failure" */
  condition_display_name?: string;
  discharge_date?: string; // ISO date
  phone?: string | null;
  channel?: Channel;
  status: PatientStatus;
  created_at?: string;
  /** Alerts the backend still considers open, embedded in GET /patients. */
  open_alerts?: AlertRecord[];
}

export interface Message {
  id: number;
  conversation_id?: number;
  sender: Sender;
  text: string;
  created_at: string; // ISO timestamp
  meta?: Record<string, unknown> | null;
}

/** Response of GET /patients/{id}/conversation */
export interface ConversationResponse {
  patient_id: number;
  patient_name: string;
  messages: Message[];
}

/** Response of POST /chat */
export interface ChatResponse {
  reply: string;
  /**
   * Present when this turn escalated. NEVER rendered on the patient
   * screen (CLAUDE.md §2 rule 4) — dashboard-only data.
   */
  alert?: AlertRecord | null;
}

/** Response of POST /checkins/{patient_id}/start */
export interface CheckinStartResponse {
  conversation_id: number;
  reply: string;
}

/** Warning signs for a condition, grouped by severity. */
export interface ConditionSigns {
  urgent: string[];
  warning: string[];
}

/** One item of GET /conditions — a pluggable checklist protocol. */
export interface ConditionProtocol {
  name: string;
  display_name: string;
  implemented: boolean;
  intro_questions: string[];
  signs: ConditionSigns;
}

/** Response of GET /stats — live dashboard control-room counters. */
export interface DashboardStats {
  patients_monitored: number;
  needs_call: number;
  checkins_today: number;
}

/** One row of GET /patients/{id}/checkins — nurse-facing history. */
export interface CheckinSummary {
  conversation_id: number;
  started_at: string; // ISO timestamp
  escalated: boolean;
  severity?: AlertSeverity | null;
  summary: string;
}

/** One escalation in the recovery report's symptom timeline. */
export interface SymptomMention {
  date: string; // ISO timestamp
  severity: AlertSeverity | string;
  signs: string[];
}

/** Response of GET /patients/{id}/report — nurse-facing recovery summary. */
export interface RecoveryReport {
  patient_id: number;
  patient_name: string;
  condition_display_name: string;
  discharge_date?: string | null;
  days_since_discharge?: number | null;
  status: PatientStatus;
  checkins_sent: number;
  checkins_answered: number;
  medication_concerns: number;
  symptom_mentions: SymptomMention[];
  alerts_total: number;
  alerts_open: number;
  generated_at: string;
}
