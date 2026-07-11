import type { PatientStatus } from "@/lib/types";

const STYLES: Record<PatientStatus, { label: string; className: string; dot: string }> = {
  good: {
    label: "All good",
    className: "bg-good-soft text-good border-good/30",
    dot: "bg-good",
  },
  watch: {
    label: "Watch",
    className: "bg-watch-soft text-watch border-watch/40",
    dot: "bg-watch",
  },
  alert: {
    label: "Needs call",
    className: "bg-alert-soft text-alert border-alert/40",
    dot: "bg-alert",
  },
};

export default function StatusPill({ status }: { status: PatientStatus }) {
  const s = STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ${s.className}`}
    >
      <span aria-hidden className={`size-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}
