from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class AsrResult:
    text: str
    confidence: float
    is_final: bool = True


class AsrError(RuntimeError):
    def __init__(self, *, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class AsrProvider(Protocol):
    async def transcribe_chunk(self, audio_bytes: bytes) -> AsrResult: ...
