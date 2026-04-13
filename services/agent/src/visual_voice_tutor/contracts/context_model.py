from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from visual_voice_tutor.contracts.whiteboard import Bounds


class ProblemContext(BaseModel):
    original_text: str
    topic: str
    grade_band: str


class TeachingState(BaseModel):
    current_goal: str
    expected_step: str
    teaching_mode: Literal[
        "guided_check",
        "hint_first",
        "scaffolded_step",
        "re_explain_simpler",
    ]
    last_system_summary: str


class RelevantShape(BaseModel):
    id: str
    type: str
    author: Literal["student", "tutor", "system"]
    text: str | None = None
    bounds: Bounds
    parent_group_id: str | None = None
    z_index: int = 0
    semantic_tag: str | None = None


class RecentBoardAction(BaseModel):
    type: str
    shape_id: str
    author: Literal["student", "tutor", "system"]
    timestamp: str


class BoardContext(BaseModel):
    full_board_thumbnail_url: str
    active_crop_url: str
    selected_shape_ids: list[str]
    relevant_shapes: list[RelevantShape]
    recent_actions: list[RecentBoardAction]


class StudentAttempt(BaseModel):
    active_region_bounds: Bounds
    recognized_text: str | None
    is_legible: bool
    confidence: float


class LearnerMemory(BaseModel):
    recurring_mistakes: list[str]
    pace_preference: Literal["slow", "neutral", "fast"]
    recent_outcomes: list[str]


class ContextTask(BaseModel):
    type: Literal[
        "judge_student_step",
        "interpret_student_drawing",
        "decide_next_hint",
        "summarize_confusion",
        "classify_error_type",
    ]
    instruction: str


class TutorContextModel(BaseModel):
    problem: ProblemContext
    teaching_state: TeachingState
    board_context: BoardContext
    student_attempt: StudentAttempt
    learner_memory: LearnerMemory
    task: ContextTask
