from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from visual_voice_tutor.contracts.stream_events import AnchorTiming


@dataclass(slots=True, frozen=True)
class TtsAudioFormat:
    encoding: str
    sample_rate_hz: int
    channels: int
    mime_type: str


@dataclass(slots=True)
class TtsSynthesisResult:
    utterance_id: str
    audio_id: str
    duration_ms: int
    anchors: list[AnchorTiming]
    audio_bytes: bytes
    audio_format: TtsAudioFormat


class TtsSynthesisError(RuntimeError):
    def __init__(self, *, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class TtsProvider(Protocol):
    async def synthesize(
        self, *, utterance_id: str, text: str, anchor_names: list[str]
    ) -> TtsSynthesisResult: ...
