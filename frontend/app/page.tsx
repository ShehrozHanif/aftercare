import Link from "next/link";

/**
 * / — landing / pitch page (CLAUDE.md §9).
 * Self-explanatory in ~5 seconds: two-part hero, a 3-step "how it works",
 * a safety badge, and the two app entrances. Staggered entrance animation
 * degrades to instant under prefers-reduced-motion (globals.css).
 */

const STEPS = [
  {
    title: "Daily check-in",
    body: "The patient gets a 2-minute chat and answers in their own words — no forms, no jargon.",
    icon: (
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    ),
  },
  {
    title: "Spots the warning signs",
    body: "AfterCare reads the reply against that condition's discharge guidance — the way a nurse would.",
    icon: <path d="M22 12h-4l-3 9L9 3l-3 9H2" />,
  },
  {
    title: "Flags a nurse",
    body: "The moment something looks wrong, a human is alerted to call the patient — today, not next week.",
    icon: (
      <>
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
      </>
    ),
  },
];

export default function Home() {
  return (
    <main className="relative flex min-h-dvh flex-1 flex-col overflow-x-clip px-5 py-6">
      {/* Soft calming backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(60rem 40rem at 50% -10%, var(--color-pine-soft), transparent 70%)",
        }}
      />

      <div className="mx-auto my-auto w-full max-w-3xl text-center">
        {/* Eyebrow */}
        <span className="rise-in inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-3 py-1 text-xs font-semibold text-pine shadow-card">
          <span aria-hidden className="size-1.5 rounded-full bg-good" />
          AI post-discharge follow-up
        </span>

        {/* Logo + wordmark */}
        <div className="rise-in mt-5 flex items-center justify-center gap-2.5" style={{ animationDelay: "60ms" }}>
          <span className="flex size-11 items-center justify-center rounded-2xl bg-pine text-xl font-bold text-white shadow-card">
            A
          </span>
          <span className="text-2xl font-bold tracking-tight text-pine">AfterCare</span>
        </div>

        {/* Two-part hero */}
        <h1
          className="rise-in mt-5 text-balance text-[2rem] font-bold leading-[1.12] tracking-tight text-ink sm:text-5xl"
          style={{ animationDelay: "120ms" }}
        >
          When patients go home,
          <br className="hidden sm:block" /> nobody follows up.{" "}
          <span className="text-pine">AfterCare does.</span>
        </h1>

        <p
          className="rise-in mx-auto mt-3.5 max-w-xl text-pretty text-base leading-relaxed text-ink-soft sm:text-lg"
          style={{ animationDelay: "180ms" }}
        >
          A friendly daily check-in that understands how each patient is really
          feeling at home — and pulls in a nurse the instant something looks wrong.
        </p>

        {/* How it works */}
        <ol
          className="rise-in mt-7 grid gap-3 text-left sm:grid-cols-3"
          style={{ animationDelay: "240ms" }}
          aria-label="How AfterCare works"
        >
          {STEPS.map((step, i) => (
            <li
              key={step.title}
              className="relative rounded-2xl border border-line bg-card p-4 shadow-card"
            >
              <div className="flex items-center gap-2.5">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-pine-soft text-pine">
                  <svg
                    aria-hidden
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    {step.icon}
                  </svg>
                </span>
                <span className="text-xs font-bold uppercase tracking-wide text-ink-soft">
                  Step {i + 1}
                </span>
              </div>
              <p className="mt-3 text-sm font-bold text-ink">{step.title}</p>
              <p className="mt-1 text-sm leading-snug text-ink-soft">{step.body}</p>
            </li>
          ))}
        </ol>

        {/* Safety badge */}
        <div
          className="rise-in mx-auto mt-5 flex max-w-xl items-center gap-3 rounded-2xl border border-good/30 bg-good-soft px-4 py-2.5 text-left"
          style={{ animationDelay: "300ms" }}
        >
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-good/15 text-good">
            <svg
              aria-hidden
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </span>
          <p className="text-sm leading-snug text-ink">
            <span className="font-bold">Never diagnoses. Never prescribes.</span>{" "}
            A human always makes the medical decision.
          </p>
        </div>

        {/* App entrances */}
        <nav
          className="rise-in mt-6 grid gap-3 sm:grid-cols-2"
          style={{ animationDelay: "360ms" }}
          aria-label="App screens"
        >
          <Link
            href="/patient"
            className="group rounded-2xl bg-pine px-5 py-4 text-left text-lg font-semibold text-white shadow-card transition-colors hover:bg-pine-deep"
          >
            <span className="flex items-center justify-between">
              Patient check-in
              <svg
                aria-hidden
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                className="transition-transform group-hover:translate-x-1"
              >
                <path
                  d="M4 10h11M10 4.5 15.5 10 10 15.5"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <span className="block text-sm font-normal text-white/75">
              WhatsApp-style daily chat
            </span>
          </Link>
          <Link
            href="/dashboard"
            className="group rounded-2xl border border-line bg-card px-5 py-4 text-left text-lg font-semibold text-pine shadow-card transition-colors hover:bg-pine-soft"
          >
            <span className="flex items-center justify-between">
              Care-team dashboard
              <svg
                aria-hidden
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                className="transition-transform group-hover:translate-x-1"
              >
                <path
                  d="M4 10h11M10 4.5 15.5 10 10 15.5"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <span className="block text-sm font-normal text-ink-soft">
              Live patient status &amp; escalations
            </span>
          </Link>
        </nav>

        <p
          className="rise-in mt-5 text-xs text-ink-soft"
          style={{ animationDelay: "420ms" }}
        >
          Synthetic demo data · built for the Sofstica SGTDP hackathon
        </p>
      </div>
    </main>
  );
}
