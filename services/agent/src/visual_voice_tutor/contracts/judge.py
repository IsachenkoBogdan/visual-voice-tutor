from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class JudgeResponse(BaseModel):
    recognized_content: str
    is_legible: bool
    is_correct: bool | None
    confidence: float
    error_type: str | None
    teacher_response_mode: Literal[
        "give_small_hint",
        "ask_for_clarification",
        "re_explain_simpler",
    ]
    next_hint: str
