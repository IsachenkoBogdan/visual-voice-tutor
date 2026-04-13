export type StreamEventType =
  | "status"
  | "utterance.start"
  | "utterance.delta"
  | "utterance.ready"
  | "utterance.audio.chunk"
  | "utterance.audio.end"
  | "board.action"
  | "board.batch_done"
  | "check.question"
  | "memory.updated"
  | "asr.partial"
  | "asr.final"
  | "final"
  | "error"
  | "interrupt";

export type ConnectionState = "idle" | "connecting" | "connected" | "disconnected" | "error";
export type AudioPlaybackState = "idle" | "buffering" | "playing" | "ended" | "fallback" | "error";

export interface EventEnvelopeBase {
  type: StreamEventType;
  request_id: string;
  session_id: string;
  turn_id: string;
  timestamp: string;
}

export interface Bounds {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface BoardShapeSnapshot {
  id: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  text?: string | null;
  author?: "student" | "tutor" | "system";
  semantic_tag?: string | null;
}

export interface CheckStepPayload {
  problem_text: string;
  expected_step: string;
  recognized_text?: string | null;
  active_region_bounds: Bounds;
  relevant_shapes: BoardShapeSnapshot[];
}

export type BoardActionSchedule =
  | { mode: "at_start" }
  | { mode: "at_end" }
  | { mode: "anchor"; anchor_id: string; offset_ms: number };

export type WhiteboardAction =
  | {
      type: "create_text";
      shape_id: string;
      x: number;
      y: number;
      text: string;
    }
  | {
      type: "create_shape";
      shape_id: string;
      x: number;
      y: number;
      w: number;
      h: number;
      shape: "rectangle" | "ellipse";
      label?: string | null;
    }
  | {
      type: "update_text";
      shape_id: string;
      text: string;
    }
  | {
      type: "delete_shape";
      shape_id: string;
    }
  | {
      type: "highlight_region";
      region_id: string;
      bounds: Bounds;
      label?: string | null;
    }
  | {
      type: "reveal_group";
      group_id: string;
    }
  | {
      type: "focus_region";
      region_id: string;
      bounds: Bounds;
    }
  | {
      type: "draw_arrow";
      shape_id: string;
      from_x: number;
      from_y: number;
      to_x: number;
      to_y: number;
      label?: string | null;
    }
  | {
      type: "pulse_region";
      region_id: string;
      bounds: Bounds;
    };

export interface PlannedBoardAction {
  action_id: string;
  schedule: BoardActionSchedule;
  action: WhiteboardAction;
}

export interface AnchorTiming {
  anchor_id: string;
  kind: "bookmark";
  name: string;
  time_ms: number;
}

export interface StatusEvent extends EventEnvelopeBase {
  type: "status";
  payload: {
    stage: string;
    message: string;
  };
}

export interface UtteranceStartEvent extends EventEnvelopeBase {
  type: "utterance.start";
  payload: {
    utterance_id: string;
    text: string;
    audio_id: string;
  };
}

export interface UtteranceDeltaEvent extends EventEnvelopeBase {
  type: "utterance.delta";
  payload: {
    utterance_id: string;
    text: string;
  };
}

export interface UtteranceReadyEvent extends EventEnvelopeBase {
  type: "utterance.ready";
  payload: {
    utterance_id: string;
    duration_ms: number;
    anchors: AnchorTiming[];
    encoding: string;
    sample_rate_hz: number;
    channels: number;
    has_audio: boolean;
    fallback_reason?: string | null;
  };
}

export interface UtteranceAudioChunkEvent extends EventEnvelopeBase {
  type: "utterance.audio.chunk";
  payload: {
    utterance_id: string;
    seq: number;
    chunk_b64: string;
    chunk_size_bytes: number;
    encoding: string;
    sample_rate_hz: number;
    channels: number;
  };
}

export interface UtteranceAudioEndEvent extends EventEnvelopeBase {
  type: "utterance.audio.end";
  payload: {
    utterance_id: string;
    total_chunks: number;
    total_bytes: number;
  };
}

export interface BoardActionEvent extends EventEnvelopeBase {
  type: "board.action";
  payload: PlannedBoardAction;
}

export interface BoardBatchDoneEvent extends EventEnvelopeBase {
  type: "board.batch_done";
  payload: {
    batch_id: string;
    step_id: string;
  };
}

export interface CheckQuestionEvent extends EventEnvelopeBase {
  type: "check.question";
  payload: {
    question: string;
    expected_mode: "short_text" | "voice" | "multiple_choice";
  };
}

export interface MemoryUpdatedEvent extends EventEnvelopeBase {
  type: "memory.updated";
  payload: {
    updated: string[];
  };
}

export interface AsrPartialEvent extends EventEnvelopeBase {
  type: "asr.partial";
  payload: {
    text: string;
    confidence: number;
  };
}

export interface AsrFinalEvent extends EventEnvelopeBase {
  type: "asr.final";
  payload: {
    text: string;
    confidence: number;
  };
}

export interface FinalEvent extends EventEnvelopeBase {
  type: "final";
  payload: {
    result: "ok" | "needs_reexplanation" | "completed" | "uncertain";
    summary: string;
  };
}

export interface ErrorEvent extends EventEnvelopeBase {
  type: "error";
  payload: {
    code: string;
    message: string;
    retryable: boolean;
  };
}

export interface InterruptEvent extends EventEnvelopeBase {
  type: "interrupt";
  payload: {
    reason: string;
    cancel_from_turn_id: string;
  };
}

export type StreamEvent =
  | StatusEvent
  | UtteranceStartEvent
  | UtteranceDeltaEvent
  | UtteranceReadyEvent
  | UtteranceAudioChunkEvent
  | UtteranceAudioEndEvent
  | BoardActionEvent
  | BoardBatchDoneEvent
  | CheckQuestionEvent
  | MemoryUpdatedEvent
  | AsrPartialEvent
  | AsrFinalEvent
  | FinalEvent
  | ErrorEvent
  | InterruptEvent;

export interface TranscriptEntry {
  id: string;
  role: "system" | "tutor" | "runtime";
  text: string;
  timestamp: string;
}

const VALID_EVENT_TYPES: Set<StreamEventType> = new Set([
  "status",
  "utterance.start",
  "utterance.delta",
  "utterance.ready",
  "utterance.audio.chunk",
  "utterance.audio.end",
  "board.action",
  "board.batch_done",
  "check.question",
  "memory.updated",
  "asr.partial",
  "asr.final",
  "final",
  "error",
  "interrupt",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parseStreamEvent(raw: string): StreamEvent | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) {
      return null;
    }

    if (
      typeof parsed.type !== "string" ||
      !VALID_EVENT_TYPES.has(parsed.type as StreamEventType) ||
      typeof parsed.request_id !== "string" ||
      typeof parsed.session_id !== "string" ||
      typeof parsed.turn_id !== "string" ||
      typeof parsed.timestamp !== "string" ||
      !isRecord(parsed.payload)
    ) {
      return null;
    }

    return parsed as unknown as StreamEvent;
  } catch {
    return null;
  }
}
