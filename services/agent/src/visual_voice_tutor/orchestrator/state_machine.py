from __future__ import annotations

from enum import StrEnum


class TurnStage(StrEnum):
    BUILDING_CONTEXT = "building_context"
    PLANNING_STEP = "planning_step"
    SYNTHESIZING_TTS = "synthesizing_tts"
    STREAMING_TIMELINE = "streaming_timeline"
    COMPLETED = "completed"


class OrchestratorStateMachine:
    def __init__(self) -> None:
        self.stage = TurnStage.BUILDING_CONTEXT

    def advance(self, next_stage: TurnStage) -> TurnStage:
        self.stage = next_stage
        return self.stage
