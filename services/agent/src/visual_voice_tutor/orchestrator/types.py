from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from visual_voice_tutor.contracts.whiteboard import PlannedBoardAction


class TutoringStep(BaseModel):
    step_id: str
    narration: str
    anchor_names: list[str] = Field(default_factory=list)
    board_actions: list[PlannedBoardAction] = Field(default_factory=list)
    check_question: str
    final_result: Literal["ok", "needs_reexplanation"]
    final_summary: str
