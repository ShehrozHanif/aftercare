import type { PatientStatus } from "@/lib/types";
import type { ReactNode } from "react";

const ICONS: Record<PatientStatus, ReactNode> = {
  // check
  good: <path d="M20 6 9 17l-5-5" />,
  // eye (keeping an eye on them)
  watch: (
    <>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  // phone (needs a call)
  alert: (
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" />
  ),
};

const STYLES: Record<PatientStatus, { label: string; className: string }> = {
  good: { label: "All good", className: "bg-good-soft text-good border-good/30" },
  watch: { label: "Watch", className: "bg-watch-soft text-watch border-watch/40" },
  alert: { label: "Needs call", className: "bg-alert-soft text-alert border-alert/40" },
};

export default function StatusPill({ status }: { status: PatientStatus }) {
  const s = STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ${s.className}`}
    >
      <svg
        aria-hidden
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {ICONS[status]}
      </svg>
      {s.label}
    </span>
  );
}
