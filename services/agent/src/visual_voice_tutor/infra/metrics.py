from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RuntimeMetrics:
    request_latency_ms: list[float] = field(default_factory=list)
    asr_latency_ms: list[float] = field(default_factory=list)
    tts_latency_ms: list[float] = field(default_factory=list)
    tool_call_errors_total: int = 0
    fallback_triggered_total: int = 0
    session_completion_total: int = 0
    voice_board_desync_total: int = 0


class MetricsCollector:
    def __init__(self) -> None:
        self._metrics = RuntimeMetrics()

    def record_request_latency(self, latency_ms: float) -> None:
        self._metrics.request_latency_ms.append(latency_ms)

    def record_asr_latency(self, latency_ms: float) -> None:
        self._metrics.asr_latency_ms.append(latency_ms)

    def record_tts_latency(self, latency_ms: float) -> None:
        self._metrics.tts_latency_ms.append(latency_ms)

    def increment_tool_errors(self) -> None:
        self._metrics.tool_call_errors_total += 1

    def increment_fallback(self) -> None:
        self._metrics.fallback_triggered_total += 1

    def increment_completed_sessions(self) -> None:
        self._metrics.session_completion_total += 1

    def increment_desync(self) -> None:
        self._metrics.voice_board_desync_total += 1

    def snapshot(self) -> dict[str, float | int]:
        return {
            "request_latency_p50_ms": _p50(self._metrics.request_latency_ms),
            "asr_latency_p50_ms": _p50(self._metrics.asr_latency_ms),
            "tts_latency_p50_ms": _p50(self._metrics.tts_latency_ms),
            "tool_call_errors_total": self._metrics.tool_call_errors_total,
            "fallback_triggered_total": self._metrics.fallback_triggered_total,
            "session_completion_total": self._metrics.session_completion_total,
            "voice_board_desync_total": self._metrics.voice_board_desync_total,
        }


def _p50(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    return sorted_values[len(sorted_values) // 2]
