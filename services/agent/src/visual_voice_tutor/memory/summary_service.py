from __future__ import annotations

from visual_voice_tutor.contracts.judge import JudgeResponse
from visual_voice_tutor.orchestrator.types import TutoringStep


def build_session_summary(step: TutoringStep, judge: JudgeResponse) -> str:
    correctness = "верно" if judge.is_correct else "нужна доработка"
    return (
        f"Шаг {step.step_id}: {correctness}. "
        f"Подсказка: {judge.next_hint} "
        f"Распознанный ввод: {judge.recognized_content}."
    )
