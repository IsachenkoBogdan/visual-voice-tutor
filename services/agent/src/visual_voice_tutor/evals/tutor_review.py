from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TutorReviewResult:
    clarity: int
    pedagogy: int
    age_appropriateness: int


def default_review() -> TutorReviewResult:
    """Stub for human-eval contract."""

    return TutorReviewResult(clarity=4, pedagogy=4, age_appropriateness=5)
