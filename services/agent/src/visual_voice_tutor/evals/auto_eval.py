from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AutoEvalResult:
    tutor_explanation_score: float
    voice_board_sync_success: bool


def run_auto_eval() -> AutoEvalResult:
    """Stub for automated regression scoring."""

    return AutoEvalResult(tutor_explanation_score=0.92, voice_board_sync_success=True)
