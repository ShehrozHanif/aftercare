/**
 * Typed API client for the AfterCare backend (contract: CLAUDE.md §8).
 *
 * Base URL comes from NEXT_PUBLIC_API_URL (never hardcoded elsewhere).
 * Mock mode:
 *   - forced with NEXT_PUBLIC_USE_MOCKS=1, or
 *   - automatic per-call fallback when the backend is unreachable
 *     (network error — HTTP errors from a live backend still throw).
 * Pages can subscribe to mock-mode state to show a subtle badge.
 */

import type {
  AlertRecord,
  ChatResponse,
  CheckinStartResponse,
  CheckinSummary,
  ConversationResponse,
  Patient,
  RecoveryReport,
} from "./types";
import {
  mockAckAlert,
  mockChat,
  mockGetCheckins,
  mockGetConversation,
  mockGetPatients,
  mockGetReport,
  mockResolvePatient,
  mockStartCheckin,
} from "./mocks";

const BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const FORCE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "1";

// --- mock-mode state -------------------------------------------------------

let mockActive = FORCE_MOCKS;
const mockListeners = new Set<(active: boolean) => void>();

export function isMockMode(): boolean {
  return mockActive;
}

/** Subscribe to mock-mode changes; returns an unsubscribe function. */
export function onMockModeChange(cb: (active: boolean) => void): () => void {
  mockListeners.add(cb);
  return () => {
    mockListeners.delete(cb);
  };
}

function setMockActive(active: boolean) {
  if (active !== mockActive) {
    mockActive = active;
    mockListeners.forEach((cb) => cb(active));
  }
}

// --- request helper --------------------------------------------------------

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `${init?.method ?? "GET"} ${path} -> ${res.status}`);
  }
  return (await res.json()) as T;
}

/**
 * Try the real backend; on a *network* failure fall back to the typed mock
 * and flip the mock badge on. An HTTP error from a reachable backend is a
 * real contract problem and is re-thrown, never silently mocked.
 */
async function withFallback<T>(real: () => Promise<T>, mock: () => T): Promise<T> {
  if (FORCE_MOCKS) return mock();
  try {
    const result = await real();
    setMockActive(false);
    return result;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    // fetch rejects with TypeError on network failure / backend down
    setMockActive(true);
    return mock();
  }
}

// --- API surface (§8 routes) ------------------------------------------------

export function sendChat(patientId: number, message: string): Promise<ChatResponse> {
  return withFallback(
    () =>
      request<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({ patient_id: patientId, message }),
      }),
    () => mockChat(patientId, message)
  );
}

export function getPatients(): Promise<Patient[]> {
  return withFallback(() => request<Patient[]>("/patients"), mockGetPatients);
}

export function getConversation(patientId: number): Promise<ConversationResponse> {
  return withFallback(
    () => request<ConversationResponse>(`/patients/${patientId}/conversation`),
    () => mockGetConversation(patientId)
  );
}

export function ackAlert(alertId: number): Promise<AlertRecord> {
  return withFallback(
    () => request<AlertRecord>(`/alerts/${alertId}/ack`, { method: "POST" }),
    () => mockAckAlert(alertId)
  );
}

export function getCheckins(patientId: number): Promise<CheckinSummary[]> {
  return withFallback(
    () => request<CheckinSummary[]>(`/patients/${patientId}/checkins`),
    () => mockGetCheckins(patientId)
  );
}

export function getReport(patientId: number): Promise<RecoveryReport> {
  return withFallback(
    () => request<RecoveryReport>(`/patients/${patientId}/report`),
    () => mockGetReport(patientId)
  );
}

export function resolvePatient(patientId: number): Promise<Patient> {
  return withFallback(
    () => request<Patient>(`/patients/${patientId}/resolve`, { method: "POST" }),
    () => mockResolvePatient(patientId)
  );
}

export function startCheckin(patientId: number): Promise<CheckinStartResponse> {
  return withFallback(
    () =>
      request<CheckinStartResponse>(`/checkins/${patientId}/start`, {
        method: "POST",
      }),
    () => mockStartCheckin(patientId)
  );
}
