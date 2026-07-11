import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-5 flex size-14 items-center justify-center rounded-2xl bg-pine text-2xl font-bold text-white shadow-card">
          A
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-pine">AfterCare</h1>
        <p className="mt-2 text-ink-soft">
          Post-discharge check-ins that pull in a nurse the moment something&rsquo;s
          wrong. Never diagnoses — a human always makes the call.
        </p>

        <nav className="mt-8 grid gap-3" aria-label="App screens">
          <Link
            href="/patient"
            className="rounded-2xl bg-pine px-5 py-4 text-lg font-semibold text-white shadow-card transition-colors hover:bg-pine-deep"
          >
            Patient check-in
            <span className="block text-sm font-normal text-white/75">
              WhatsApp-style daily chat
            </span>
          </Link>
          <Link
            href="/dashboard"
            className="rounded-2xl border border-line bg-card px-5 py-4 text-lg font-semibold text-pine shadow-card transition-colors hover:bg-pine-soft"
          >
            Care-team dashboard
            <span className="block text-sm font-normal text-ink-soft">
              Live patient status &amp; escalations
            </span>
          </Link>
        </nav>
      </div>
    </main>
  );
}
