from __future__ import annotations

from visual_voice_tutor.board.roi_extractor import extract_active_region
from visual_voice_tutor.board.shape_mapper import map_board_shapes
from visual_voice_tutor.contracts.context_model import (
    BoardContext,
    ContextTask,
    LearnerMemory,
    ProblemContext,
    RecentBoardAction,
    StudentAttempt,
    TeachingState,
    TutorContextModel,
)
from visual_voice_tutor.contracts.runtime_commands import CheckStepPayload
from visual_voice_tutor.memory.learner_store import LearnerMemoryRecord


def build_mock_context(*, learner_memory: LearnerMemoryRecord) -> TutorContextModel:
    relevant_shapes = map_board_shapes(
        [
            {
                "id": "student_line_1",
                "type": "text",
                "text": "3x+8=15",
                "bounds": {"x": 132, "y": 126, "w": 126, "h": 28},
                "semantic_tag": "student_current_line",
            }
        ]
    )

    return TutorContextModel(
        problem=ProblemContext(
            original_text="Реши уравнение 3(x+2)=15",
            topic="linear_equation",
            grade_band="4-7",
        ),
        teaching_state=TeachingState(
            current_goal="check student expansion step",
            expected_step="3x+6=15",
            teaching_mode="guided_check",
            last_system_summary="The tutor asked the student to expand brackets.",
        ),
        board_context=BoardContext(
            full_board_thumbnail_url="mock://board/full",
            active_crop_url="mock://board/crop",
            selected_shape_ids=["student_line_1"],
            relevant_shapes=relevant_shapes,
            recent_actions=[
                RecentBoardAction(
                    type="edit_text",
                    shape_id="student_line_1",
                    author="student",
                    timestamp="2026-04-14T12:34:58Z",
                )
            ],
        ),
        student_attempt=StudentAttempt(
            active_region_bounds=extract_active_region(),
            recognized_text="3x+8=15",
            is_legible=True,
            confidence=0.84,
        ),
        learner_memory=LearnerMemory(
            recurring_mistakes=learner_memory.recurring_mistakes,
            pace_preference=learner_memory.pace_preference,
            recent_outcomes=learner_memory.recent_outcomes,
        ),
        task=ContextTask(
            type="judge_student_step",
            instruction="Determine whether the student expanded the brackets correctly.",
        ),
    )


def build_context_from_check_request(
    *,
    payload: CheckStepPayload,
    learner_memory: LearnerMemoryRecord,
) -> TutorContextModel:
    relevant_shapes = map_board_shapes(
        [
            {
                "id": shape.id,
                "type": shape.type,
                "text": shape.text,
                "bounds": {"x": shape.x, "y": shape.y, "w": shape.w, "h": shape.h},
                "semantic_tag": shape.semantic_tag,
            }
            for shape in payload.relevant_shapes
        ]
    )

    selected_ids = [shape.id for shape in payload.relevant_shapes[:8]]

    return TutorContextModel(
        problem=ProblemContext(
            original_text=payload.problem_text,
            topic="linear_equation",
            grade_band="4-7",
        ),
        teaching_state=TeachingState(
            current_goal="check student step",
            expected_step=payload.expected_step,
            teaching_mode="guided_check",
            last_system_summary="The tutor is checking the student's current line.",
        ),
        board_context=BoardContext(
            full_board_thumbnail_url="inmemory://full_board",
            active_crop_url="inmemory://active_crop",
            selected_shape_ids=selected_ids,
            relevant_shapes=relevant_shapes,
            recent_actions=[
                RecentBoardAction(
                    type="check_step",
                    shape_id=selected_ids[0] if selected_ids else "shape_unknown",
                    author="student",
                    timestamp="2026-04-14T12:34:58Z",
                )
            ],
        ),
        student_attempt=StudentAttempt(
            active_region_bounds=extract_active_region(payload.active_region_bounds.model_dump(mode="python")),
            recognized_text=payload.recognized_text,
            is_legible=bool(payload.recognized_text),
            confidence=0.85 if payload.recognized_text else 0.45,
        ),
        learner_memory=LearnerMemory(
            recurring_mistakes=learner_memory.recurring_mistakes,
            pace_preference=learner_memory.pace_preference,
            recent_outcomes=learner_memory.recent_outcomes,
        ),
        task=ContextTask(
            type="judge_student_step",
            instruction=(
                "Check whether the student's current equation step is correct. "
                "If wrong, provide the smallest helpful hint."
            ),
        ),
    )
