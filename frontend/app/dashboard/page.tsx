"use client";

/**
 * /dashboard — nurse care-team view (CLAUDE.md §9, §13).
 * Polls GET /patients every 3s so an escalation appears live.
 * Escalated patients sort to the top with a red row + alert reason,
 * matched signs, transcript panel and an acknowledge action.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ackAlert, getCheckins, getConversation, getPatients } from "@/lib/api";
import type {
  CheckinSummary,
  ConversationResponse,
  Patient,
  PatientStatus,
} from "@/lib/types";
import MockBadge from "@/components/MockBadge";
import StatusPill from "@/components/StatusPill";

const POLL_MS = 3000;

const PROTOCOLS = [
  { name: "Heart Failure", state: "Active" as const },
  { name: "Post-surgical", state: "Stub" as const },
  { name: "COPD", state: "Stub" as const },
];

/**
 * Effective triage status. The backend occasionally reports status "good"
 * while open alerts exist (and may leave "alert" after all alerts are
 * acknowledged) — the nurse view keys on open alerts first.
 */
function effectiveStatus(p: Patient): PatientStatus {
  const hasOpen = (p.open_alerts ?? []).some((a) => a.status === "open");
  if (hasOpen) return "alert";
  if (p.status === "alert") return "watch"; // escalation handled, keep an eye
  return p.status;
}

const STATUS_RANK: Record<PatientStatus, number> = { alert: 0, watch: 1, good: 2 };

function newestAlertTime(p: Patient): number {
  return Math.max(0, ...(p.open_alerts ?? []).map((a) => Date.parse(a.created_at)));
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export default function Dashboard() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [pollError, setPollError] = useState(false);
  const [transcriptFor, setTranscriptFor] = useState<number | null>(null);
  const [conversation, setConversation] = useState<ConversationResponse | null>(null);
  const [checkins, setCheckins] = useState<CheckinSummary[] | null>(null);
  const [ackInFlight, setAckInFlight] = useState<Set<number>>(new Set());
  // ids of patients that just escalated (for the attention pulse)
  const [pulseIds, setPulseIds] = useState<Set<number>>(new Set());
  const prevAlertedRef = useRef<Set<number> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await getPatients();
      setPollError(false);
      setLastUpdated(new Date());
      setPatients(list);

      const alerted = new Set(
        list.filter((p) => effectiveStatus(p) === "alert").map((p) => p.id)
      );
      const prev = prevAlertedRef.current;
      if (prev) {
        const fresh = [...alerted].filter((id) => !prev.has(id));
        if (fresh.length > 0) setPulseIds(new Set(fresh));
      }
      prevAlertedRef.current = alerted;
    } catch {
      setPollError(true);
    }
  }, []);

  // Live polling (§9 — the demo's money moment).
  useEffect(() => {
    void refresh();
    const iv = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(iv);
  }, [refresh]);

  // Load (and keep refreshing) the open transcript + check-in history.
  useEffect(() => {
    if (transcriptFor === null) {
      setConversation(null);
      setCheckins(null);
      return;
    }
    let cancelled = false;
    const load = () => {
      getConversation(transcriptFor)
        .then((c) => {
          if (!cancelled) setConversation(c);
        })
        .catch(() => {});
      getCheckins(transcriptFor)
        .then((h) => {
          if (!cancelled) setCheckins(h);
        })
        .catch(() => {});
    };
    void load();
    const iv = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, [transcriptFor]);

  const onAck = async (alertId: number) => {
    setAckInFlight((prev) => new Set(prev).add(alertId));
    try {
      await ackAlert(alertId);
      await refresh();
    } catch {
      // leave the alert visible; nurse can retry
    } finally {
      setAckInFlight((prev) => {
        const next = new Set(prev);
        next.delete(alertId);
        return next;
      });
    }
  };

  const sorted = [...patients].sort((a, b) => {
    const rank = STATUS_RANK[effectiveStatus(a)] - STATUS_RANK[effectiveStatus(b)];
    if (rank !== 0) return rank;
    return newestAlertTime(b) - newestAlertTime(a);
  });

  const needsCall = sorted.filter((p) => effectiveStatus(p) === "alert").length;

  return (
    <div className="flex min-h-dvh flex-1 flex-col">
      {/* Header */}
      <header className="border-b border-line bg-card">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <Link
            href="/"
            className="flex size-9 items-center justify-center rounded-xl bg-pine text-lg font-bold text-white"
            aria-label="AfterCare home"
          >
            A
          </Link>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-bold leading-tight">
              Care-team dashboard
            </h1>
            <p className="text-xs text-ink-soft">
              {needsCall > 0 ? (
                <span className="font-semibold text-alert">
                  {needsCall} patient{needsCall > 1 ? "s" : ""} need
                  {needsCall === 1 ? "s" : ""} a call
                </span>
              ) : (
                "All patients stable"
              )}
            </p>
          </div>
          <p
            className="flex items-center gap-1.5 text-xs text-ink-soft"
            role="status"
            aria-label={pollError ? "Live updates paused" : "Live updates on"}
          >
            <span
              aria-hidden
              className={`size-2 rounded-full ${pollError ? "bg-watch" : "bg-good"}`}
            />
            {pollError
              ? "Reconnecting…"
              : lastUpdated
                ? `Live · ${formatTime(lastUpdated.toISOString())}`
                : "Connecting…"}
          </p>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-6xl flex-1 gap-4 p-4 lg:grid-cols-[1fr_320px]">
        {/* Patient list */}
        <main aria-label="Patients">
          <ul className="flex flex-col gap-2.5">
            {sorted.map((p) => {
              const status = effectiveStatus(p);
              const openAlerts = (p.open_alerts ?? []).filter((a) => a.status === "open");
              const escalated = status === "alert";
              return (
                <li
                  key={p.id}
                  className={`rounded-xl border p-4 shadow-card transition-colors ${
                    escalated
                      ? `border-alert/50 bg-alert-soft ${pulseIds.has(p.id) ? "alert-pulse" : ""}`
                      : "border-line bg-card"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                    <span className="text-[15px] font-bold">{p.name}</span>
                    <span className="rounded-full bg-pine-soft px-2.5 py-0.5 text-xs font-medium text-pine-deep">
                      {p.condition_display_name ?? p.condition}
                    </span>
                    {p.discharge_date && (
                      <span className="text-xs text-ink-soft">
                        Discharged {p.discharge_date}
                      </span>
                    )}
                    <span className="text-xs uppercase tracking-wide text-ink-soft/80">
                      {p.channel ?? "web"}
                    </span>
                    <span className="ml-auto">
                      <StatusPill status={status} />
                    </span>
                  </div>

                  {escalated &&
                    openAlerts.map((alert) => (
                      <div
                        key={alert.id}
                        className="mt-3 rounded-lg border border-alert/30 bg-card/70 p-3"
                      >
                        <p className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-wide text-alert">
                          {alert.severity === "URGENT" ? "Urgent" : "Warning"}
                          <span className="font-normal normal-case tracking-normal text-ink-soft">
                            {formatTime(alert.created_at)}
                          </span>
                        </p>
                        <p className="mt-1 text-sm leading-snug">{alert.reason}</p>
                        {alert.matched_signs.length > 0 && (
                          <ul
                            className="mt-2 flex flex-wrap gap-1.5"
                            aria-label="Matched warning signs"
                          >
                            {alert.matched_signs.map((sign) => (
                              <li
                                key={sign}
                                className="rounded-full border border-alert/30 bg-alert-soft px-2 py-0.5 text-xs text-ink"
                              >
                                {sign}
                              </li>
                            ))}
                          </ul>
                        )}
                        <div className="mt-3 flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => setTranscriptFor(p.id)}
                            className="rounded-lg bg-pine px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-pine-deep"
                          >
                            View conversation
                          </button>
                          <button
                            type="button"
                            onClick={() => void onAck(alert.id)}
                            disabled={ackInFlight.has(alert.id)}
                            className="rounded-lg border border-line bg-card px-3 py-1.5 text-xs font-semibold text-ink transition-colors hover:bg-page disabled:opacity-50"
                          >
                            {ackInFlight.has(alert.id) ? "Acknowledging…" : "Acknowledge"}
                          </button>
                        </div>
                      </div>
                    ))}

                  {!escalated && (
                    <div className="mt-2.5">
                      <button
                        type="button"
                        onClick={() => setTranscriptFor(p.id)}
                        className="text-xs font-semibold text-pine underline-offset-2 hover:underline"
                      >
                        View conversation
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
            {sorted.length === 0 && (
              <li className="rounded-xl border border-line bg-card p-6 text-center text-sm text-ink-soft shadow-card">
                {pollError ? "Can't reach the AfterCare service." : "Loading patients…"}
              </li>
            )}
          </ul>
        </main>

        {/* Side column: protocols */}
        <aside aria-label="Condition protocols" className="lg:order-none">
          <div className="rounded-xl border border-line bg-card p-4 shadow-card">
            <h2 className="text-sm font-bold">Condition protocols</h2>
            <p className="mt-0.5 text-xs text-ink-soft">
              Adding a condition is a new checklist, not a new app.
            </p>
            <ul className="mt-3 flex flex-col gap-2">
              {PROTOCOLS.map((proto) => (
                <li
                  key={proto.name}
                  className="flex items-center justify-between rounded-lg border border-line px-3 py-2 text-sm"
                >
                  {proto.name}
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      proto.state === "Active"
                        ? "bg-good-soft text-good"
                        : "bg-page text-ink-soft"
                    }`}
                  >
                    {proto.state}
                  </span>
                </li>
              ))}
            </ul>
            <button
              type="button"
              title="Coming soon"
              aria-describedby="add-protocol-note"
              className="mt-3 w-full rounded-lg border-2 border-dashed border-line px-3 py-2 text-sm font-semibold text-ink-soft transition-colors hover:border-pine/50 hover:text-pine"
            >
              + Add condition protocol
            </button>
            <p id="add-protocol-note" className="sr-only">
              Coming soon — protocols are pluggable checklist modules.
            </p>
          </div>
        </aside>
      </div>

      {/* Transcript panel */}
      {transcriptFor !== null && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Conversation with ${conversation?.patient_name ?? "patient"}`}
          className="fixed inset-0 z-40 flex justify-end bg-ink/40"
          onClick={() => setTranscriptFor(null)}
        >
          <div
            className="flex h-full w-full max-w-md flex-col bg-card shadow-card"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="font-bold">
                {conversation?.patient_name ?? "Conversation"}
                <span className="ml-2 text-xs font-normal text-ink-soft">transcript</span>
              </h2>
              <button
                type="button"
                onClick={() => setTranscriptFor(null)}
                aria-label="Close transcript"
                className="rounded-full p-2 text-ink-soft transition-colors hover:bg-page hover:text-ink"
              >
                <svg aria-hidden width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path
                    d="m3 3 10 10M13 3 3 13"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </header>
            {checkins !== null && checkins.length > 0 && (
              <section
                aria-label="Recent check-ins"
                className="border-b border-line px-4 py-3"
              >
                <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-ink-soft">
                  Recent check-ins
                </h3>
                <ol className="flex flex-col gap-1.5">
                  {checkins.slice(0, 5).map((c) => (
                    <li key={c.conversation_id} className="flex items-start gap-2 text-xs">
                      <span className="w-16 shrink-0 pt-0.5 text-ink-soft">
                        {formatDay(c.started_at)}
                      </span>
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          c.escalated
                            ? c.severity === "URGENT"
                              ? "bg-alert text-white"
                              : "bg-alert-soft text-alert"
                            : "bg-good-soft text-good"
                        }`}
                      >
                        {c.escalated ? c.severity ?? "FLAGGED" : "All clear"}
                      </span>
                      <span className="min-w-0 truncate text-ink" title={c.summary}>
                        {c.summary}
                      </span>
                    </li>
                  ))}
                </ol>
              </section>
            )}
            <div className="flex-1 overflow-y-auto bg-page px-4 py-4">
              {conversation === null ? (
                <p className="text-center text-sm text-ink-soft">Loading transcript…</p>
              ) : conversation.messages.length === 0 ? (
                <p className="text-center text-sm text-ink-soft">No messages yet.</p>
              ) : (
                <ol className="flex flex-col gap-2">
                  {conversation.messages.map((m) => (
                    <li
                      key={m.id}
                      className={`max-w-[85%] rounded-bubble px-3.5 py-2 text-sm leading-relaxed shadow-card ${
                        m.sender === "agent"
                          ? "self-start rounded-bl-md bg-card"
                          : "self-end rounded-br-md bg-pine text-white"
                      }`}
                    >
                      <span
                        className={`block text-[10px] font-semibold uppercase tracking-wide ${
                          m.sender === "agent" ? "text-ink-soft" : "text-white/70"
                        }`}
                      >
                        {m.sender === "agent" ? "AfterCare agent" : "Patient"} ·{" "}
                        {formatTime(m.created_at)}
                      </span>
                      {m.text}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        </div>
      )}
      <MockBadge />
    </div>
  );
}
