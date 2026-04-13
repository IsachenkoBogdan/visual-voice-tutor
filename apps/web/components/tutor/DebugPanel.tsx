"use client";

import { StreamEvent } from "@/lib/contracts";
import { AudioPlayerSnapshot } from "@/lib/audio-player";
import { SchedulerSnapshot } from "@/lib/scheduler";

interface DebugPanelProps {
  scheduler: SchedulerSnapshot;
  audio: AudioPlayerSnapshot;
  lastEvent: StreamEvent | null;
  rawEventsReceived: number;
  appliedActions: number;
}

export function DebugPanel({ scheduler, audio, lastEvent, rawEventsReceived, appliedActions }: DebugPanelProps) {
  const elapsedMs = null;
  const driftMs = null;

  return (
    <section className="rounded-xl border border-zinc-200 bg-zinc-950 p-3 text-xs text-zinc-100 shadow-sm">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-300">Debug</h2>
      <div className="grid gap-2 text-zinc-300 sm:grid-cols-2">
        <div>raw_events: {rawEventsReceived}</div>
        <div>applied_actions: {appliedActions}</div>
        <div>pending_timers: {scheduler.pendingActions}</div>
        <div>queued_before_playback: {scheduler.queuedBeforePlayback}</div>
        <div>anchor_count: {scheduler.anchorCount}</div>
        <div>playback_started: {String(scheduler.playbackStarted)}</div>
        <div>turn_id: {scheduler.turnId ?? "none"}</div>
        <div>interrupted: {String(scheduler.interrupted)}</div>
        <div>audio_state: {audio.state}</div>
        <div>audio_utterance: {audio.activeUtteranceId ?? "none"}</div>
        <div>audio_chunks: {audio.bufferedChunks}</div>
        <div>audio_bytes: {audio.bufferedBytes}</div>
        <div>expected_chunks: {audio.expectedChunks ?? "unknown"}</div>
        <div>elapsed_ms: {elapsedMs ?? "n/a"}</div>
        <div>drift_ms: {driftMs ?? "n/a"}</div>
      </div>
      <pre className="mt-3 max-h-56 overflow-auto rounded-md bg-zinc-900 p-2 text-[11px] leading-5">
        {JSON.stringify(lastEvent, null, 2)}
      </pre>
    </section>
  );
}
