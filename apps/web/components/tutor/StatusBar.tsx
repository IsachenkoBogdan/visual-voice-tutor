"use client";

import { Button } from "@/components/ui/button";
import { AudioPlaybackState, ConnectionState } from "@/lib/contracts";
import { MicState } from "@/lib/mic-recorder";

const connectionClass: Record<ConnectionState, string> = {
  idle: "bg-zinc-200 text-zinc-700",
  connecting: "bg-amber-100 text-amber-800",
  connected: "bg-emerald-100 text-emerald-800",
  disconnected: "bg-zinc-200 text-zinc-700",
  error: "bg-rose-100 text-rose-800",
};

const audioClass: Record<AudioPlaybackState, string> = {
  idle: "bg-zinc-100 text-zinc-700",
  buffering: "bg-amber-100 text-amber-800",
  playing: "bg-sky-100 text-sky-800",
  ended: "bg-emerald-100 text-emerald-800",
  fallback: "bg-orange-100 text-orange-800",
  error: "bg-rose-100 text-rose-800",
};

interface StatusBarProps {
  connectionState: ConnectionState;
  audioState: AudioPlaybackState;
  micState: MicState;
  stage: string;
  message: string;
  turnId: string | null;
  utteranceId: string | null;
  onRunMockTurn: () => void;
  onCheckStep: () => void;
  onStartMic: () => void;
  onStopMic: () => void;
  onInterrupt: () => void;
}

export function StatusBar({
  connectionState,
  audioState,
  micState,
  stage,
  message,
  turnId,
  utteranceId,
  onRunMockTurn,
  onCheckStep,
  onStartMic,
  onStopMic,
  onInterrupt,
}: StatusBarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white/90 p-3 shadow-sm">
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className={`rounded-full px-2 py-0.5 font-semibold ${connectionClass[connectionState]}`}>
            ws:{connectionState}
          </span>
          <span className={`rounded-full px-2 py-0.5 font-semibold ${audioClass[audioState]}`}>
            audio:{audioState}
          </span>
          <span className="rounded-full bg-violet-100 px-2 py-0.5 font-semibold text-violet-800">mic:{micState}</span>
          <span className="text-zinc-500">{turnId ?? "turn_not_started"}</span>
        </div>
        <div className="text-xs text-zinc-500">{utteranceId ?? "utterance_not_started"}</div>
        <div className="text-sm text-zinc-700">
          <span className="font-semibold text-zinc-900">{stage || "idle"}</span>
          <span className="mx-2 text-zinc-400">|</span>
          <span>{message || "Waiting for stream events"}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button type="button" variant="default" onClick={onRunMockTurn}>
          Run Mock Turn
        </Button>
        <Button type="button" variant="secondary" onClick={onCheckStep}>
          Check My Step
        </Button>
        <Button type="button" variant="outline" onClick={onStartMic}>
          Start Mic
        </Button>
        <Button type="button" variant="outline" onClick={onStopMic}>
          Stop Mic
        </Button>
        <Button type="button" variant="outline" onClick={onInterrupt}>
          Interrupt
        </Button>
      </div>
    </div>
  );
}
