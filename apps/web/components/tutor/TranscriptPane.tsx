"use client";

import { TranscriptEntry } from "@/lib/contracts";

interface TranscriptPaneProps {
  entries: TranscriptEntry[];
  finalSummary: string | null;
}

export function TranscriptPane({ entries, finalSummary }: TranscriptPaneProps) {
  return (
    <section className="flex h-full min-h-0 flex-col rounded-xl border border-zinc-200 bg-white/90 shadow-sm">
      <header className="border-b border-zinc-200 px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-600">Transcript</h2>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {entries.length === 0 ? (
          <p className="text-sm text-zinc-500">No events yet.</p>
        ) : (
          entries.map((entry) => (
            <article key={entry.id} className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2">
              <div className="mb-1 flex items-center justify-between text-xs text-zinc-500">
                <span className="uppercase tracking-wide">{entry.role}</span>
                <time>{new Date(entry.timestamp).toLocaleTimeString()}</time>
              </div>
              <p className="text-sm text-zinc-800">{entry.text}</p>
            </article>
          ))
        )}
      </div>

      {finalSummary ? (
        <footer className="border-t border-zinc-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          <span className="font-semibold">Final:</span> {finalSummary}
        </footer>
      ) : null}
    </section>
  );
}
