import Link from "next/link";

export default function HomePage() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-zinc-950 px-6 py-20 text-zinc-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(16,185,129,0.2),transparent_40%),radial-gradient(circle_at_80%_10%,rgba(14,165,233,0.25),transparent_42%),radial-gradient(circle_at_50%_95%,rgba(250,204,21,0.16),transparent_35%)]" />

      <section className="relative z-10 w-full max-w-3xl rounded-2xl border border-zinc-700/60 bg-zinc-900/70 p-8 shadow-2xl backdrop-blur">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300">
          Visual Voice Tutor
        </p>

        <h1 className="max-w-2xl text-3xl font-semibold leading-tight text-white md:text-4xl">
          Realtime tutor runtime shell: typed WebSocket stream, timeline scheduler, and synced board actions.
        </h1>

        <p className="mt-4 max-w-2xl text-zinc-300">
          This is the first realistic runtime slice for the tutoring loop. Open the tutor route to run a mocked
          end-to-end turn from backend orchestration to whiteboard rendering.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/tutor"
            className="rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-400"
          >
            Open Tutor Runtime
          </Link>
          <Link
            href="/learners"
            className="rounded-lg border border-zinc-600 px-5 py-2.5 text-sm font-semibold text-zinc-100 transition hover:border-zinc-300"
          >
            Learners
          </Link>
          <Link
            href="/billing"
            className="rounded-lg border border-zinc-600 px-5 py-2.5 text-sm font-semibold text-zinc-100 transition hover:border-zinc-300"
          >
            Billing
          </Link>
          <a
            href="http://localhost:8000/health"
            className="rounded-lg border border-zinc-600 px-5 py-2.5 text-sm font-semibold text-zinc-100 transition hover:border-zinc-300"
            target="_blank"
            rel="noreferrer"
          >
            Backend Health
          </a>
        </div>
      </section>
    </main>
  );
}
