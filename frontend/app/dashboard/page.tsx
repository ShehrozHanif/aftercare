"use client";

/**
 * /dashboard — nurse care-team view (CLAUDE.md §9, §13).
 * Polls GET /patients every 3s so an escalation appears live.
 * Escalated patients sort to the top with a red row + alert reason,
 * matched signs, transcript panel and an acknowledge action.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ackAlert,
  getCheckins,
  getConditions,
  getConversation,
  getPatients,
  getReport,
  getStats,
  resolvePatient,
} from "@/lib/api";
import type {
  CheckinSummary,
  ConditionProtocol,
  ConversationResponse,
  DashboardStats,
  Patient,
  PatientStatus,
  RecoveryReport,
} from "@/lib/types";
import MockBadge from "@/components/MockBadge";
import StatusPill from "@/components/StatusPill";
import Avatar from "@/components/Avatar";

const POLL_MS = 3000;

/** Animate a number toward `value` (eased, ~500ms). Instant under
 * reduced-motion. Kept cheap and layout-stable via tabular figures. */
function CountUp({ value }: { value: number }) {
  const [display, setDisplay] = useState(0);
  const prev = useRef(0);
  useEffect(() => {
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const from = prev.current;
    const to = value;
    // Show the real number immediately when animation can't run smoothly
    // (reduced-motion, or a hidden tab where rAF is paused — never leave a
    // stale 0 on screen).
    if (reduce || from === to || (typeof document !== "undefined" && document.hidden)) {
      setDisplay(to);
      prev.current = to;
      return;
    }
    const duration = 500;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
      else prev.current = to;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{display}</>;
}

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
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [pollError, setPollError] = useState(false);
  const [transcriptFor, setTranscriptFor] = useState<number | null>(null);
  const [conversation, setConversation] = useState<ConversationResponse | null>(null);
  const [checkins, setCheckins] = useState<CheckinSummary[] | null>(null);
  const [reportFor, setReportFor] = useState<number | null>(null);
  const [report, setReport] = useState<RecoveryReport | null>(null);
  const [conditions, setConditions] = useState<ConditionProtocol[]>([]);
  const [protocolFor, setProtocolFor] = useState<string | null>(null);
  const [showAddInfo, setShowAddInfo] = useState(false);
  const [ackInFlight, setAckInFlight] = useState<Set<number>>(new Set());
  const [resolveInFlight, setResolveInFlight] = useState<Set<number>>(new Set());
  // ids of patients that just escalated (for the attention pulse)
  const [pulseIds, setPulseIds] = useState<Set<number>>(new Set());
  const prevAlertedRef = useRef<Set<number> | null>(null);
  // toast notifications for fresh escalations + a header count flash
  const [toasts, setToasts] = useState<{ key: number; name: string }[]>([]);
  const [headerFlash, setHeaderFlash] = useState(false);
  const toastKeyRef = useRef(0);
  // FLIP animation: remember each row's screen position between renders so a
  // newly escalated row visibly slides to the top instead of snapping there.
  const rowRefs = useRef(new Map<number, HTMLLIElement>());
  const prevRects = useRef(new Map<number, DOMRect>());

  const refresh = useCallback(async () => {
    try {
      const [list, liveStats] = await Promise.all([getPatients(), getStats()]);
      setPollError(false);
      setLastUpdated(new Date());
      setPatients(list);
      setStats(liveStats);

      const alerted = new Set(
        list.filter((p) => effectiveStatus(p) === "alert").map((p) => p.id)
      );
      const prev = prevAlertedRef.current;
      if (prev) {
        const fresh = [...alerted].filter((id) => !prev.has(id));
        if (fresh.length > 0) {
          setPulseIds(new Set(fresh));
          const nameById = new Map(list.map((p) => [p.id, p.name]));
          fresh.forEach((id) => {
            const key = toastKeyRef.current++;
            const name = nameById.get(id) ?? "A patient";
            setToasts((t) => [...t, { key, name }]);
            // auto-dismiss (toast UX: 3–5s), never steals focus
            setTimeout(
              () => setToasts((t) => t.filter((x) => x.key !== key)),
              5000
            );
          });
          setHeaderFlash(true);
          setTimeout(() => setHeaderFlash(false), 1100);
        }
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

  // Condition protocols are static (code registry) — fetch once.
  useEffect(() => {
    getConditions()
      .then(setConditions)
      .catch(() => {});
  }, []);

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

  // Load the recovery report when its panel opens (one-shot per open).
  useEffect(() => {
    if (reportFor === null) {
      setReport(null);
      return;
    }
    let cancelled = false;
    getReport(reportFor)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [reportFor]);

  // FLIP: after each render, slide any row that changed position from its old
  // spot to its new one (the escalation "jump to top" moment). Runs before
  // paint so there's no flicker; respects reduced-motion.
  useLayoutEffect(() => {
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const newRects = new Map<number, DOMRect>();
    rowRefs.current.forEach((el, id) => newRects.set(id, el.getBoundingClientRect()));
    if (!reduce) {
      newRects.forEach((newRect, id) => {
        const prev = prevRects.current.get(id);
        if (!prev) return;
        const dy = prev.top - newRect.top;
        if (Math.abs(dy) < 2) return;
        const el = rowRefs.current.get(id);
        if (!el) return;
        el.style.transition = "none";
        el.style.transform = `translateY(${dy}px)`;
        requestAnimationFrame(() => {
          el.style.transition = "transform 380ms cubic-bezier(0.22, 1, 0.36, 1)";
          el.style.transform = "";
        });
      });
    }
    prevRects.current = newRects;
  });

  const onResolve = async (patientId: number) => {
    setResolveInFlight((prev) => new Set(prev).add(patientId));
    try {
      await resolvePatient(patientId);
      await refresh();
    } catch {
      // refused (e.g. an alert reopened meanwhile) — row stays as is
    } finally {
      setResolveInFlight((prev) => {
        const next = new Set(prev);
        next.delete(patientId);
        return next;
      });
    }
  };

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
  const protocol = protocolFor
    ? conditions.find((c) => c.name === protocolFor) ?? null
    : null;

  return (
    <div className="flex min-h-dvh flex-1 flex-col">
      {/* Header */}
      <header className="border-b border-line bg-card">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <Link
            href="/"
            className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-pine to-pine-deep text-lg font-bold text-white"
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
                <span
                  className={`font-semibold text-alert ${headerFlash ? "count-flash" : ""}`}
                >
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

      {/* Live control-room stat bar */}
      <div className="mx-auto w-full max-w-6xl px-4 pt-4">
        <dl className="grid grid-cols-3 gap-2.5 sm:gap-3">
          <div className="flex items-center gap-3 rounded-xl border border-line bg-card p-3 shadow-card sm:p-4">
            <span className="hidden size-10 shrink-0 items-center justify-center rounded-xl bg-pine-soft text-pine sm:flex">
              <svg aria-hidden width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </span>
            <div className="min-w-0">
              <dd className="text-2xl font-bold leading-none tabular-nums">
                <CountUp value={patients.length} />
              </dd>
              <dt className="mt-1 text-[11px] font-medium uppercase tracking-wide text-ink-soft">
                Patients monitored
              </dt>
            </div>
          </div>

          <div
            className={`flex items-center gap-3 rounded-xl border p-3 shadow-card sm:p-4 ${
              needsCall > 0 ? "border-alert/40 bg-alert-soft" : "border-line bg-card"
            }`}
          >
            <span
              className={`hidden size-10 shrink-0 items-center justify-center rounded-xl sm:flex ${
                needsCall > 0 ? "bg-alert/15 text-alert" : "bg-pine-soft text-pine"
              }`}
            >
              <svg aria-hidden width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" />
              </svg>
            </span>
            <div className="min-w-0">
              <dd
                className={`text-2xl font-bold leading-none tabular-nums ${
                  needsCall > 0 ? "text-alert" : ""
                } ${headerFlash ? "count-flash" : ""}`}
              >
                <CountUp value={needsCall} />
              </dd>
              <dt className="mt-1 text-[11px] font-medium uppercase tracking-wide text-ink-soft">
                Needs a call
              </dt>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-line bg-card p-3 shadow-card sm:p-4">
            <span className="hidden size-10 shrink-0 items-center justify-center rounded-xl bg-pine-soft text-pine sm:flex">
              <svg aria-hidden width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 11.5V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14l4-4h6" />
                <path d="m16 19 2 2 4-4" />
              </svg>
            </span>
            <div className="min-w-0">
              <dd className="text-2xl font-bold leading-none tabular-nums">
                {stats ? <CountUp value={stats.checkins_today} /> : "—"}
              </dd>
              <dt className="mt-1 text-[11px] font-medium uppercase tracking-wide text-ink-soft">
                Check-ins today
              </dt>
            </div>
          </div>
        </dl>
      </div>

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
                  ref={(el) => {
                    if (el) rowRefs.current.set(p.id, el);
                    else rowRefs.current.delete(p.id);
                  }}
                  className={`rounded-xl border p-4 shadow-card transition-colors ${
                    escalated
                      ? `border-alert/50 bg-alert-soft ${pulseIds.has(p.id) ? "alert-pulse" : ""}`
                      : "border-line bg-card"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Avatar name={p.name} size={40} />
                    <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1.5">
                      <span className="text-[15px] font-bold">{p.name}</span>
                      <span className="rounded-full bg-pine-soft px-2.5 py-0.5 text-xs font-medium text-pine-deep">
                        {p.condition_display_name ?? p.condition}
                      </span>
                      {p.discharge_date && (
                        <span className="text-xs text-ink-soft">
                          Discharged {p.discharge_date}
                        </span>
                      )}
                      <span className="ml-auto">
                        <StatusPill status={status} />
                      </span>
                    </div>
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
                            onClick={() => setReportFor(p.id)}
                            className="rounded-lg border border-pine/40 bg-card px-3 py-1.5 text-xs font-semibold text-pine transition-colors hover:bg-pine-soft"
                          >
                            View report
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
                    <div className="mt-2.5 flex flex-wrap items-center gap-4">
                      <button
                        type="button"
                        onClick={() => setTranscriptFor(p.id)}
                        className="text-xs font-semibold text-pine underline-offset-2 hover:underline"
                      >
                        View conversation
                      </button>
                      <button
                        type="button"
                        onClick={() => setReportFor(p.id)}
                        className="text-xs font-semibold text-pine underline-offset-2 hover:underline"
                      >
                        View report
                      </button>
                      {status === "watch" && (
                        <button
                          type="button"
                          onClick={() => void onResolve(p.id)}
                          disabled={resolveInFlight.has(p.id)}
                          className="rounded-lg border border-good/50 bg-good-soft px-3 py-1.5 text-xs font-semibold text-good transition-colors hover:bg-good hover:text-white disabled:opacity-50"
                        >
                          {resolveInFlight.has(p.id)
                            ? "Updating…"
                            : "Mark as all good"}
                        </button>
                      )}
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
              Adding a condition is a new checklist, not a new app. Tap one to
              see its warning signs.
            </p>
            <ul className="mt-3 flex flex-col gap-2">
              {conditions.map((c) => {
                const total = c.signs.urgent.length + c.signs.warning.length;
                return (
                  <li key={c.name}>
                    <button
                      type="button"
                      onClick={() => setProtocolFor(c.name)}
                      className="flex w-full items-center gap-2 rounded-lg border border-line px-3 py-2 text-left text-sm transition-colors hover:border-pine/40 hover:bg-pine-soft/40"
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium">
                          {c.display_name}
                        </span>
                        <span className="text-xs text-ink-soft">
                          {total} warning signs
                        </span>
                      </span>
                      <span className="rounded-full bg-good-soft px-2 py-0.5 text-xs font-semibold text-good">
                        {c.implemented ? "Active" : "Draft"}
                      </span>
                      <svg
                        aria-hidden
                        width="14"
                        height="14"
                        viewBox="0 0 16 16"
                        fill="none"
                        className="shrink-0 text-ink-soft"
                      >
                        <path
                          d="m6 4 4 4-4 4"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                  </li>
                );
              })}
              {conditions.length === 0 && (
                <li className="rounded-lg border border-line px-3 py-2 text-xs text-ink-soft">
                  Loading protocols…
                </li>
              )}
            </ul>
            <button
              type="button"
              onClick={() => setShowAddInfo((v) => !v)}
              aria-expanded={showAddInfo}
              className="mt-3 w-full rounded-lg border-2 border-dashed border-line px-3 py-2 text-sm font-semibold text-ink-soft transition-colors hover:border-pine/50 hover:text-pine"
            >
              + Add condition protocol
            </button>
            {showAddInfo && (
              <div className="mt-2 rounded-lg border border-pine/20 bg-pine-soft/40 p-3 text-xs leading-relaxed text-ink">
                A new protocol is <span className="font-semibold">one checklist file</span> —
                the warning signs from a hospital&rsquo;s discharge guidance. The
                agent engine never changes. It stays a manual step on purpose:
                a real deployment gates every new protocol behind{" "}
                <span className="font-semibold">clinician review</span> before it
                can flag a patient.
              </div>
            )}
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
      {/* Recovery report panel */}
      {reportFor !== null && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Recovery report for ${report?.patient_name ?? "patient"}`}
          className="fixed inset-0 z-40 flex justify-end bg-ink/40"
          onClick={() => setReportFor(null)}
        >
          <div
            className="flex h-full w-full max-w-md flex-col bg-card shadow-card"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="font-bold">
                {report?.patient_name ?? "Recovery report"}
                <span className="ml-2 text-xs font-normal text-ink-soft">
                  recovery report
                </span>
              </h2>
              <button
                type="button"
                onClick={() => setReportFor(null)}
                aria-label="Close report"
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
            <div className="flex-1 overflow-y-auto bg-page px-4 py-4">
              {report === null ? (
                <p className="text-center text-sm text-ink-soft">Loading report…</p>
              ) : (
                <div className="flex flex-col gap-3">
                  <section className="rounded-xl border border-line bg-card p-3 shadow-card">
                    <p className="text-xs text-ink-soft">
                      {report.condition_display_name}
                      {report.days_since_discharge !== null &&
                        report.days_since_discharge !== undefined &&
                        ` · day ${report.days_since_discharge} after discharge`}
                    </p>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                      <div className="rounded-lg bg-page p-2">
                        <p className="text-lg font-bold">
                          {report.checkins_answered}/{report.checkins_sent}
                        </p>
                        <p className="text-[10px] uppercase tracking-wide text-ink-soft">
                          Check-ins answered
                        </p>
                      </div>
                      <div className="rounded-lg bg-page p-2">
                        <p
                          className={`text-lg font-bold ${
                            report.alerts_open > 0 ? "text-alert" : ""
                          }`}
                        >
                          {report.alerts_open}
                          <span className="text-xs font-normal text-ink-soft">
                            {" "}
                            / {report.alerts_total}
                          </span>
                        </p>
                        <p className="text-[10px] uppercase tracking-wide text-ink-soft">
                          Open / total alerts
                        </p>
                      </div>
                      <div className="rounded-lg bg-page p-2">
                        <p
                          className={`text-lg font-bold ${
                            report.medication_concerns > 0 ? "text-watch" : ""
                          }`}
                        >
                          {report.medication_concerns}
                        </p>
                        <p className="text-[10px] uppercase tracking-wide text-ink-soft">
                          Medication concerns
                        </p>
                      </div>
                    </div>
                    {report.checkins_sent > report.checkins_answered && (
                      <p className="mt-2 rounded-lg bg-watch-soft px-2 py-1 text-xs text-ink">
                        {report.checkins_sent - report.checkins_answered} check-in
                        {report.checkins_sent - report.checkins_answered > 1
                          ? "s"
                          : ""}{" "}
                        went unanswered — silence can be a signal too.
                      </p>
                    )}
                  </section>

                  <section
                    aria-label="Reported symptoms since discharge"
                    className="rounded-xl border border-line bg-card p-3 shadow-card"
                  >
                    <h3 className="text-[11px] font-semibold uppercase tracking-wide text-ink-soft">
                      Reported symptoms since discharge
                    </h3>
                    {report.symptom_mentions.length === 0 ? (
                      <p className="mt-2 text-sm text-ink-soft">
                        No warning signs reported. 💙
                      </p>
                    ) : (
                      <ol className="mt-2 flex flex-col gap-2">
                        {report.symptom_mentions.map((m, i) => (
                          <li key={i} className="text-xs">
                            <span className="text-ink-soft">{formatDay(m.date)}</span>
                            <span
                              className={`ml-2 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                m.severity === "URGENT"
                                  ? "bg-alert text-white"
                                  : "bg-alert-soft text-alert"
                              }`}
                            >
                              {m.severity}
                            </span>
                            <span className="mt-1 block text-ink">
                              {m.signs.join(" · ")}
                            </span>
                          </li>
                        ))}
                      </ol>
                    )}
                  </section>

                  <p className="text-center text-[10px] text-ink-soft">
                    Aggregates what the patient reported — clinical decisions
                    always rest with the care team.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {/* Condition protocol detail — proves the checklists are real content */}
      {protocolFor !== null && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`${protocol?.display_name ?? "Condition"} protocol`}
          className="fixed inset-0 z-40 flex justify-end bg-ink/40"
          onClick={() => setProtocolFor(null)}
        >
          <div
            className="flex h-full w-full max-w-md flex-col bg-card shadow-card"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="font-bold">
                {protocol?.display_name ?? "Condition"}
                <span className="ml-2 text-xs font-normal text-ink-soft">
                  protocol
                </span>
              </h2>
              <button
                type="button"
                onClick={() => setProtocolFor(null)}
                aria-label="Close protocol"
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
            <div className="flex-1 overflow-y-auto bg-page px-4 py-4">
              {protocol === null ? (
                <p className="text-center text-sm text-ink-soft">Loading…</p>
              ) : (
                <div className="flex flex-col gap-3">
                  <p className="rounded-lg bg-watch-soft px-3 py-2 text-xs leading-relaxed text-ink">
                    From published discharge guidance. The agent uses these signs
                    to decide when to flag a nurse — it never shows them to the
                    patient or names a diagnosis.{" "}
                    <span className="font-semibold">
                      Requires clinician review before real-world use.
                    </span>
                  </p>

                  <section className="rounded-xl border border-alert/30 bg-card p-3 shadow-card">
                    <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-alert">
                      Urgent
                      <span className="rounded-full bg-alert-soft px-1.5 py-0.5 text-[10px] font-semibold">
                        {protocol.signs.urgent.length}
                      </span>
                      <span className="font-normal normal-case tracking-normal text-ink-soft">
                        escalate immediately
                      </span>
                    </h3>
                    <ul className="mt-2 flex flex-col gap-1.5">
                      {protocol.signs.urgent.map((s) => (
                        <li key={s} className="flex gap-2 text-sm text-ink">
                          <span aria-hidden className="mt-1.5 size-1.5 shrink-0 rounded-full bg-alert" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </section>

                  <section className="rounded-xl border border-watch/40 bg-card p-3 shadow-card">
                    <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-watch">
                      Warning
                      <span className="rounded-full bg-watch-soft px-1.5 py-0.5 text-[10px] font-semibold">
                        {protocol.signs.warning.length}
                      </span>
                      <span className="font-normal normal-case tracking-normal text-ink-soft">
                        same-day callback
                      </span>
                    </h3>
                    <ul className="mt-2 flex flex-col gap-1.5">
                      {protocol.signs.warning.map((s) => (
                        <li key={s} className="flex gap-2 text-sm text-ink">
                          <span aria-hidden className="mt-1.5 size-1.5 shrink-0 rounded-full bg-watch" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </section>

                  <p className="text-center text-[10px] text-ink-soft">
                    Same engine, different checklist — this is the whole
                    &ldquo;new disease is a new file&rdquo; design.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Escalation toasts — announce a fresh red flag without stealing focus */}
      <div
        className="pointer-events-none fixed inset-x-0 top-3 z-50 flex flex-col items-center gap-2 px-4"
        role="status"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((t) => (
          <div
            key={t.key}
            className="toast-in pointer-events-auto flex items-center gap-2.5 rounded-xl border border-alert/40 bg-card px-4 py-2.5 shadow-card"
          >
            <span aria-hidden className="alert-pulse size-2.5 shrink-0 rounded-full bg-alert" />
            <span className="text-sm font-medium text-ink">
              <span className="font-bold text-alert">{t.name}</span> needs a call
            </span>
          </div>
        ))}
      </div>
      <MockBadge />
    </div>
  );
}
