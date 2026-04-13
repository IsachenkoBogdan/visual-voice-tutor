from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from visual_voice_tutor.infra.supabase import SupabaseLearnerBackend


class LearnerMemoryRecord(BaseModel):
    recurring_mistakes: list[str] = Field(default_factory=list)
    pace_preference: Literal["slow", "neutral", "fast"] = "neutral"
    recent_outcomes: list[str] = Field(default_factory=list)


class SupabaseLearnerStore:
    def __init__(self, backend: SupabaseLearnerBackend) -> None:
        self._backend = backend

    async def get(self, learner_id: str) -> LearnerMemoryRecord:
        raw = await self._backend.get_learner_memory(learner_id)
        return LearnerMemoryRecord.model_validate(raw)

    async def put(self, learner_id: str, record: LearnerMemoryRecord) -> None:
        await self._backend.upsert_learner_memory(learner_id, record.model_dump(mode="json"))
