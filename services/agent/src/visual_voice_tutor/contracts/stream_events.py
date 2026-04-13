from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from visual_voice_tutor.contracts.whiteboard import PlannedBoardAction


class BasePayload(BaseModel):
    pass


class StatusPayload(BasePayload):
    stage: str
    message: str


class UtteranceStartPayload(BasePayload):
    utterance_id: str
    text: str
    audio_id: str


class UtteranceDeltaPayload(BasePayload):
    utterance_id: str
    text: str


class AnchorTiming(BaseModel):
    anchor_id: str
    kind: Literal["bookmark"] = "bookmark"
    name: str
    time_ms: int


class UtteranceReadyPayload(BasePayload):
    utterance_id: str
    duration_ms: int
    anchors: list[AnchorTiming]
    encoding: str
    sample_rate_hz: int
    channels: int
    has_audio: bool
    fallback_reason: str | None = None


class UtteranceAudioChunkPayload(BasePayload):
    utterance_id: str
    seq: int
    chunk_b64: str
    chunk_size_bytes: int
    encoding: str
    sample_rate_hz: int
    channels: int


class UtteranceAudioEndPayload(BasePayload):
    utterance_id: str
    total_chunks: int
    total_bytes: int


class BoardBatchDonePayload(BasePayload):
    batch_id: str
    step_id: str


class CheckQuestionPayload(BasePayload):
    question: str
    expected_mode: Literal["short_text", "voice", "multiple_choice"] = "short_text"


class MemoryUpdatedPayload(BasePayload):
    updated: list[str]


class FinalPayload(BasePayload):
    result: Literal["ok", "needs_reexplanation", "completed", "uncertain"]
    summary: str


class ErrorPayload(BasePayload):
    code: str
    message: str
    retryable: bool


class InterruptPayload(BasePayload):
    reason: str
    cancel_from_turn_id: str


class AsrPartialPayload(BasePayload):
    text: str
    confidence: float


class AsrFinalPayload(BasePayload):
    text: str
    confidence: float


class StreamEventBase(BaseModel):
    request_id: str
    session_id: str
    turn_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StatusEvent(StreamEventBase):
    type: Literal["status"] = "status"
    payload: StatusPayload


class UtteranceStartEvent(StreamEventBase):
    type: Literal["utterance.start"] = "utterance.start"
    payload: UtteranceStartPayload


class UtteranceDeltaEvent(StreamEventBase):
    type: Literal["utterance.delta"] = "utterance.delta"
    payload: UtteranceDeltaPayload


class UtteranceReadyEvent(StreamEventBase):
    type: Literal["utterance.ready"] = "utterance.ready"
    payload: UtteranceReadyPayload


class UtteranceAudioChunkEvent(StreamEventBase):
    type: Literal["utterance.audio.chunk"] = "utterance.audio.chunk"
    payload: UtteranceAudioChunkPayload


class UtteranceAudioEndEvent(StreamEventBase):
    type: Literal["utterance.audio.end"] = "utterance.audio.end"
    payload: UtteranceAudioEndPayload


class BoardActionEvent(StreamEventBase):
    type: Literal["board.action"] = "board.action"
    payload: PlannedBoardAction


class BoardBatchDoneEvent(StreamEventBase):
    type: Literal["board.batch_done"] = "board.batch_done"
    payload: BoardBatchDonePayload


class CheckQuestionEvent(StreamEventBase):
    type: Literal["check.question"] = "check.question"
    payload: CheckQuestionPayload


class MemoryUpdatedEvent(StreamEventBase):
    type: Literal["memory.updated"] = "memory.updated"
    payload: MemoryUpdatedPayload


class FinalEvent(StreamEventBase):
    type: Literal["final"] = "final"
    payload: FinalPayload


class ErrorEvent(StreamEventBase):
    type: Literal["error"] = "error"
    payload: ErrorPayload


class InterruptEvent(StreamEventBase):
    type: Literal["interrupt"] = "interrupt"
    payload: InterruptPayload


class AsrPartialEvent(StreamEventBase):
    type: Literal["asr.partial"] = "asr.partial"
    payload: AsrPartialPayload


class AsrFinalEvent(StreamEventBase):
    type: Literal["asr.final"] = "asr.final"
    payload: AsrFinalPayload


StreamEvent = Annotated[
    StatusEvent
    | UtteranceStartEvent
    | UtteranceDeltaEvent
    | UtteranceReadyEvent
    | UtteranceAudioChunkEvent
    | UtteranceAudioEndEvent
    | BoardActionEvent
    | BoardBatchDoneEvent
    | CheckQuestionEvent
    | MemoryUpdatedEvent
    | FinalEvent
    | ErrorEvent
    | InterruptEvent
    | AsrPartialEvent
    | AsrFinalEvent,
    Field(discriminator="type"),
]
