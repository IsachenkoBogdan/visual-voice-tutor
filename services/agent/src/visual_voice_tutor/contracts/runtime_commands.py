from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from visual_voice_tutor.contracts.whiteboard import Bounds


class RunMockTurnCommand(BaseModel):
    type: Literal["run_mock_turn"] = "run_mock_turn"


class InterruptCommand(BaseModel):
    type: Literal["interrupt"] = "interrupt"
    turn_id: str
    reason: str = "client_interrupt"


class BoardShapeSnapshot(BaseModel):
    id: str
    type: str
    x: float
    y: float
    w: float
    h: float
    text: str | None = None
    author: Literal["student", "tutor", "system"] = "student"
    semantic_tag: str | None = None


class CheckStepPayload(BaseModel):
    problem_text: str
    expected_step: str
    recognized_text: str | None = None
    active_region_bounds: Bounds
    relevant_shapes: list[BoardShapeSnapshot] = Field(default_factory=list)


class CheckStepCommand(BaseModel):
    type: Literal["check_step"] = "check_step"
    payload: CheckStepPayload


class AsrTranscribePayload(BaseModel):
    audio_b64: str
    mime_type: str = "audio/wav"


class AsrTranscribeCommand(BaseModel):
    type: Literal["asr.transcribe"] = "asr.transcribe"
    payload: AsrTranscribePayload


RuntimeCommand = Annotated[
    RunMockTurnCommand | InterruptCommand | CheckStepCommand | AsrTranscribeCommand,
    Field(discriminator="type"),
]
