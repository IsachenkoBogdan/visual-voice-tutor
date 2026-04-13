from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from visual_voice_tutor.infra.redis import RedisSessionBackend


class SessionState(BaseModel):
    session_id: str
    student_id: str | None = None
    grade_band: str = "4-7"
    dialog_history: list[str] = Field(default_factory=list)
    current_problem: dict[str, Any] | None = None
    retrieved_tasks: list[dict[str, Any]] = Field(default_factory=list)
    current_plan: list[dict[str, Any]] = Field(default_factory=list)
    current_step_idx: int = 0
    misunderstanding_count: int = 0
    clarification_pending: bool = False
    canvas_snapshot_ref: str | None = None
    viewport_summary: dict[str, Any] | None = None
    focused_shape_ids: list[str] = Field(default_factory=list)
    last_canvas_actions: list[str] = Field(default_factory=list)
    last_spoken_hint: str | None = None
    completion_status: str | None = None


class RedisSessionStore:
    def __init__(self, backend: RedisSessionBackend) -> None:
        self._backend = backend

    async def load_or_create(self, session_id: str) -> SessionState:
        raw = await self._backend.get_session(session_id)
        if raw is None:
            return SessionState(session_id=session_id)
        return SessionState.model_validate(raw)

    async def save(self, state: SessionState) -> None:
        await self._backend.set_session(state.session_id, state.model_dump(mode="json"))
