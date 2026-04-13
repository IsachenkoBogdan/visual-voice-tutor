"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Editor } from "tldraw";

import { DebugPanel } from "@/components/tutor/DebugPanel";
import { StatusBar } from "@/components/tutor/StatusBar";
import { TranscriptPane } from "@/components/tutor/TranscriptPane";
import { WhiteboardPane } from "@/components/tutor/WhiteboardPane";
import { AudioPlayer, AudioPlayerSnapshot } from "@/lib/audio-player";
import { buildCheckStepPayload } from "@/lib/board-actions";
import {
  AudioPlaybackState,
  ConnectionState,
  PlannedBoardAction,
  StreamEvent,
  TranscriptEntry,
} from "@/lib/contracts";
import { buildApiHeaders, buildTutorWsUrl, getClientEnv } from "@/lib/env";
import { MicRecorder, MicState } from "@/lib/mic-recorder";
import { PlaybackScheduler, SchedulerSnapshot } from "@/lib/scheduler";
import { TutorWsClient } from "@/lib/ws-client";

function entry(role: TranscriptEntry["role"], text: string, timestamp: string): TranscriptEntry {
  return {
    id: `${Date.now()}-${Math.random()}`,
    role,
    text,
    timestamp,
  };
}

function toIsoNow(): string {
  return new Date().toISOString();
}

async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

const emptySchedulerSnapshot: SchedulerSnapshot = {
  turnId: null,
  anchorCount: 0,
  pendingActions: 0,
  queuedBeforePlayback: 0,
  pendingActionIds: [],
  timelineStartedAt: null,
  durationMs: null,
  playbackStarted: false,
  interrupted: false,
};

const emptyAudioSnapshot: AudioPlayerSnapshot = {
  state: "idle",
  activeUtteranceId: null,
  bufferedChunks: 0,
  bufferedBytes: 0,
  expectedChunks: null,
};

interface TutorShellProps {
  initialLearnerId?: string;
  initialUserId?: string;
}

export function TutorShell({
  initialLearnerId = "demo_learner",
  initialUserId = "demo_user",
}: TutorShellProps) {
  const env = getClientEnv();
  const schedulerRef = useRef(new PlaybackScheduler());
  const wsRef = useRef<TutorWsClient | null>(null);
  const audioRef = useRef<AudioPlayer | null>(null);
  const micRef = useRef<MicRecorder | null>(null);
  const editorRef = useRef<Editor | null>(null);
  const currentTurnIdRef = useRef<string | null>(null);

  const [sessionId] = useState(() => `sess_${Math.random().toString(36).slice(2, 10)}`);
  const [learnerId, setLearnerId] = useState(initialLearnerId);
  const [userId, setUserId] = useState(initialUserId);
  const wsUrl = useMemo(
    () => buildTutorWsUrl(env.wsUrl, sessionId, learnerId, userId, env.apiKey),
    [env.wsUrl, sessionId, learnerId, userId, env.apiKey],
  );

  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [audioState, setAudioState] = useState<AudioPlaybackState>("idle");
  const [stage, setStage] = useState("idle");
  const [statusMessage, setStatusMessage] = useState("Waiting for backend runtime");
  const [currentTurnId, setCurrentTurnId] = useState<string | null>(null);
  const [currentUtteranceId, setCurrentUtteranceId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [finalSummary, setFinalSummary] = useState<string | null>(null);
  const [lastEvent, setLastEvent] = useState<StreamEvent | null>(null);
  const [rawEventsReceived, setRawEventsReceived] = useState(0);
  const [appliedActions, setAppliedActions] = useState<PlannedBoardAction[]>([]);
  const [appliedActionsCount, setAppliedActionsCount] = useState(0);
  const [schedulerSnapshot, setSchedulerSnapshot] = useState<SchedulerSnapshot>(emptySchedulerSnapshot);
  const [audioSnapshot, setAudioSnapshot] = useState<AudioPlayerSnapshot>(emptyAudioSnapshot);
  const [problemText, setProblemText] = useState("Реши уравнение 3(x+2)=15");
  const [expectedStep, setExpectedStep] = useState("3x+6=15");
  const [recognizedText, setRecognizedText] = useState("");
  const [micState, setMicState] = useState<MicState>("idle");
  const [historySummary, setHistorySummary] = useState<string[]>([]);

  const pushTranscript = useCallback((next: TranscriptEntry) => {
    setTranscript((prev) => [...prev, next].slice(-60));
  }, []);

  const refreshSnapshots = useCallback(() => {
    setSchedulerSnapshot(schedulerRef.current.getSnapshot());
    setAudioSnapshot(audioRef.current?.getSnapshot() ?? emptyAudioSnapshot);
  }, []);

  const handleEvent = useCallback(
    (event: StreamEvent) => {
      setLastEvent(event);
      setCurrentTurnId(event.turn_id);
      currentTurnIdRef.current = event.turn_id;
      setRawEventsReceived((prev) => prev + 1);

      switch (event.type) {
        case "status":
          setStage(event.payload.stage);
          setStatusMessage(event.payload.message);
          pushTranscript(entry("system", `${event.payload.stage}: ${event.payload.message}`, event.timestamp));
          break;

        case "utterance.start":
          setCurrentUtteranceId(event.payload.utterance_id);
          pushTranscript(entry("tutor", event.payload.text, event.timestamp));
          break;

        case "utterance.delta":
          pushTranscript(entry("runtime", `delta: ${event.payload.text}`, event.timestamp));
          break;

        case "utterance.ready": {
          setCurrentUtteranceId(event.payload.utterance_id);
          setStatusMessage(`Audio metadata ready (${event.payload.duration_ms}ms)`);
          schedulerRef.current.beginTurn(event.turn_id, event.payload.duration_ms, event.payload.anchors);

          if (!event.payload.has_audio) {
            audioRef.current?.setFallbackState();
            schedulerRef.current.markPlaybackStarted(event.turn_id);
            setStatusMessage(
              event.payload.fallback_reason
                ? `TTS fallback: ${event.payload.fallback_reason}`
                : "TTS fallback: text+board mode",
            );
          }

          refreshSnapshots();
          break;
        }

        case "utterance.audio.chunk":
          audioRef.current?.enqueueChunk(event.payload);
          refreshSnapshots();
          break;

        case "utterance.audio.end":
          audioRef.current?.markEnded(event.payload);
          void audioRef.current?.startIfBuffered(event.payload.utterance_id).then((started) => {
            if (!started && audioRef.current?.getSnapshot().state === "buffering") {
              setStatusMessage("Audio buffering incomplete, waiting for chunks");
            }
            refreshSnapshots();
          });
          refreshSnapshots();
          break;

        case "board.action":
          schedulerRef.current.scheduleAction(event.payload, (action) => {
            setAppliedActions((prev) => [...prev, action]);
          });
          refreshSnapshots();
          break;

        case "board.batch_done":
          pushTranscript(entry("runtime", `Board batch done: ${event.payload.step_id}`, event.timestamp));
          break;

        case "check.question":
          pushTranscript(entry("tutor", event.payload.question, event.timestamp));
          break;

        case "memory.updated":
          pushTranscript(entry("runtime", `Memory updated: ${event.payload.updated.join(", ")}`, event.timestamp));
          break;

        case "asr.partial":
          pushTranscript(
            entry("runtime", `ASR partial (${event.payload.confidence.toFixed(2)}): ${event.payload.text}`, event.timestamp),
          );
          break;

        case "asr.final":
          setRecognizedText(event.payload.text);
          pushTranscript(
            entry("runtime", `ASR final (${event.payload.confidence.toFixed(2)}): ${event.payload.text}`, event.timestamp),
          );
          break;

        case "final":
          setFinalSummary(event.payload.summary);
          setStatusMessage(`Turn completed with result: ${event.payload.result}`);
          pushTranscript(entry("system", `Final: ${event.payload.summary}`, event.timestamp));
          break;

        case "error":
          setStatusMessage(`${event.payload.code}: ${event.payload.message}`);
          pushTranscript(entry("system", `Error: ${event.payload.message}`, event.timestamp));
          break;

        case "interrupt":
          schedulerRef.current.interrupt(event.payload.cancel_from_turn_id);
          audioRef.current?.stopAndClear();
          setStatusMessage(`Interrupted: ${event.payload.reason}`);
          pushTranscript(entry("system", `Interrupted: ${event.payload.reason}`, event.timestamp));
          refreshSnapshots();
          break;
      }
    },
    [pushTranscript, refreshSnapshots],
  );

  useEffect(() => {
    const audioPlayer = new AudioPlayer({
      onStateChange: setAudioState,
      onPlaybackStarted: () => {
        const turnId = currentTurnIdRef.current;
        if (turnId) {
          schedulerRef.current.markPlaybackStarted(turnId);
          setStatusMessage("Audio playback started");
          refreshSnapshots();
        }
      },
      onPlaybackEnded: () => {
        setStatusMessage("Audio playback ended");
        refreshSnapshots();
      },
      onError: (message) => {
        pushTranscript(entry("system", `Audio warning: ${message}`, toIsoNow()));
      },
    });
    audioRef.current = audioPlayer;

    const scheduler = schedulerRef.current;
    const micRecorder = new MicRecorder();
    micRef.current = micRecorder;
    setMicState(micRecorder.getState());
    const client = new TutorWsClient(wsUrl, {
      onConnectionStateChange: setConnectionState,
      onEvent: handleEvent,
      onRawMessage: () => refreshSnapshots(),
      onError: (message) => {
        pushTranscript(entry("system", `Runtime warning: ${message}`, toIsoNow()));
      },
    });

    wsRef.current = client;
    client.connect();

    return () => {
      scheduler.clear();
      audioPlayer.stopAndClear();
      client.disconnect();
      audioRef.current = null;
      micRef.current = null;
    };
  }, [wsUrl, handleEvent, pushTranscript, refreshSnapshots]);

  const handleRunMockTurn = useCallback(() => {
    setFinalSummary(null);
    setAppliedActions([]);
    setAppliedActionsCount(0);
    schedulerRef.current.clear();
    audioRef.current?.stopAndClear();
    refreshSnapshots();
    wsRef.current?.runMockTurn();
    pushTranscript(entry("runtime", "Requested new mock turn", toIsoNow()));
  }, [pushTranscript, refreshSnapshots]);

  const handleInterrupt = useCallback(() => {
    if (!currentTurnId) {
      return;
    }
    schedulerRef.current.interrupt(currentTurnId);
    audioRef.current?.stopAndClear();
    refreshSnapshots();
    wsRef.current?.interruptTurn(currentTurnId);
  }, [currentTurnId, refreshSnapshots]);

  const handleCheckStep = useCallback(() => {
    const editor = editorRef.current;
    if (!editor) {
      pushTranscript(entry("system", "Whiteboard editor is not ready yet", toIsoNow()));
      return;
    }

    setFinalSummary(null);
    setAppliedActions([]);
    setAppliedActionsCount(0);
    schedulerRef.current.clear();
    audioRef.current?.stopAndClear();
    refreshSnapshots();

    const payload = buildCheckStepPayload(editor, {
      problemText,
      expectedStep,
      recognizedText,
    });
    wsRef.current?.checkStep(payload);
    pushTranscript(entry("runtime", "Requested board-aware step checking", toIsoNow()));
  }, [expectedStep, problemText, pushTranscript, recognizedText, refreshSnapshots]);

  const handleLoadHistory = useCallback(async () => {
    try {
      const response = await fetch(`${env.apiBaseUrl}/api/v1/learners/${learnerId}/sessions?limit=8`, {
        headers: buildApiHeaders(env.apiKey),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = (await response.json()) as Array<{ summary: string; result: string }>;
      const summaries = data.map((item) => `${item.result}: ${item.summary}`).slice(0, 8);
      setHistorySummary(summaries);
      pushTranscript(entry("runtime", `Loaded ${summaries.length} session summaries`, toIsoNow()));
    } catch (error) {
      pushTranscript(entry("system", `Failed to load history: ${String(error)}`, toIsoNow()));
    }
  }, [env.apiBaseUrl, env.apiKey, learnerId, pushTranscript]);

  const handleMicStart = useCallback(async () => {
    const recorder = micRef.current;
    if (!recorder) {
      return;
    }
    const ok = await recorder.start();
    setMicState(recorder.getState());
    if (!ok) {
      pushTranscript(entry("system", "Microphone unavailable or permission denied", toIsoNow()));
    }
  }, [pushTranscript]);

  const handleMicStop = useCallback(async () => {
    const recorder = micRef.current;
    if (!recorder) {
      return;
    }
    const result = await recorder.stopAndCollect();
    setMicState(recorder.getState());
    if (!result) {
      return;
    }

    const encoded = await blobToBase64(result.blob);
    wsRef.current?.transcribeAudio(encoded, result.mimeType);
    pushTranscript(entry("runtime", `Submitted ASR chunk (${result.mimeType})`, toIsoNow()));
  }, [pushTranscript]);

  const handleActionApplied = useCallback(
    (actionId: string) => {
      setAppliedActionsCount((prev) => prev + 1);
      refreshSnapshots();
      pushTranscript(entry("runtime", `Applied board action: ${actionId}`, toIsoNow()));
    },
    [pushTranscript, refreshSnapshots],
  );

  return (
    <main className="flex h-full min-h-0 flex-col gap-3 p-3 md:p-4">
      <StatusBar
        connectionState={connectionState}
        audioState={audioState}
        micState={micState}
        stage={stage}
        message={statusMessage}
        turnId={currentTurnId}
        utteranceId={currentUtteranceId}
        onRunMockTurn={handleRunMockTurn}
        onCheckStep={handleCheckStep}
        onStartMic={() => {
          void handleMicStart();
        }}
        onStopMic={() => {
          void handleMicStop();
        }}
        onInterrupt={handleInterrupt}
      />

      <section className="grid gap-2 rounded-xl border border-zinc-200 bg-white/90 p-3 shadow-sm md:grid-cols-3">
        <label className="flex min-w-0 flex-col gap-1 text-xs text-zinc-600">
          User ID
          <input
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            className="rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-900"
            placeholder="demo_user"
          />
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs text-zinc-600">
          Learner ID
          <input
            value={learnerId}
            onChange={(event) => setLearnerId(event.target.value)}
            className="rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-900"
            placeholder="demo_learner"
          />
        </label>
        <div className="flex min-w-0 items-end">
          <button
            type="button"
            className="w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-700 hover:bg-zinc-50"
            onClick={() => {
              void handleLoadHistory();
            }}
          >
            Load Session History
          </button>
        </div>
      </section>

      <section className="grid gap-2 rounded-xl border border-zinc-200 bg-white/90 p-3 shadow-sm md:grid-cols-3">
        <label className="flex min-w-0 flex-col gap-1 text-xs text-zinc-600">
          Problem
          <input
            value={problemText}
            onChange={(event) => setProblemText(event.target.value)}
            className="rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-900"
            placeholder="Реши уравнение ..."
          />
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs text-zinc-600">
          Expected Step
          <input
            value={expectedStep}
            onChange={(event) => setExpectedStep(event.target.value)}
            className="rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-900"
            placeholder="3x+6=15"
          />
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs text-zinc-600">
          Recognized Text (Optional)
          <input
            value={recognizedText}
            onChange={(event) => setRecognizedText(event.target.value)}
            className="rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-900"
            placeholder="Текст с доски или ASR"
          />
        </label>
      </section>

      {historySummary.length > 0 ? (
        <section className="rounded-xl border border-zinc-200 bg-white/90 p-3 text-sm text-zinc-700 shadow-sm">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Recent Session History</h3>
          <ul className="space-y-1">
            {historySummary.map((line, index) => (
              <li key={`${index}-${line}`} className="rounded border border-zinc-100 bg-zinc-50 px-2 py-1">
                {line}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]">
        <WhiteboardPane
          actions={appliedActions}
          onActionApplied={handleActionApplied}
          onEditorReady={(editor) => {
            editorRef.current = editor;
          }}
        />

        <div className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto] gap-3">
          <TranscriptPane entries={transcript} finalSummary={finalSummary} />
          <DebugPanel
            scheduler={schedulerSnapshot}
            audio={audioSnapshot}
            lastEvent={lastEvent}
            rawEventsReceived={rawEventsReceived}
            appliedActions={appliedActionsCount}
          />
        </div>
      </section>
    </main>
  );
}
