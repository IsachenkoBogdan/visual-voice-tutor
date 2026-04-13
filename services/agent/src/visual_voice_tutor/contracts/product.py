from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class UserAccount(BaseModel):
    user_id: str
    email: str
    role: Literal["parent", "teacher", "admin"] = "parent"
    learner_ids: list[str] = Field(default_factory=list)


class LearnerProfile(BaseModel):
    learner_id: str
    display_name: str = "Learner"
    grade_band: str = "4-7"
    pace_preference: Literal["slow", "neutral", "fast"] = "neutral"
    weak_spots: list[str] = Field(default_factory=list)
    recurring_mistakes: list[str] = Field(default_factory=list)
    recent_topics: list[str] = Field(default_factory=list)


class SessionSummaryRecord(BaseModel):
    session_id: str
    turn_id: str
    learner_id: str
    result: str
    summary: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HumanEvalRecord(BaseModel):
    eval_id: str
    learner_id: str
    session_id: str
    clarity: int = Field(ge=1, le=5)
    pedagogy: int = Field(ge=1, le=5)
    age_appropriateness: int = Field(ge=1, le=5)
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AutoEvalRecord(BaseModel):
    eval_id: str
    learner_id: str
    session_id: str
    tutor_explanation_score: float = Field(ge=0.0, le=1.0)
    voice_board_sync_success: bool
    judge_human_agreement: float | None = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UsageEvent(BaseModel):
    event_id: str
    learner_id: str
    event_type: Literal["turn_completed", "asr_minute", "tts_characters"]
    units: float = 1.0
    session_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SubscriptionState(BaseModel):
    learner_id: str
    plan_id: Literal["free", "pro", "team"] = "free"
    status: Literal["inactive", "trialing", "active", "past_due", "canceled"] = "active"
    renews_at: datetime | None = None
    monthly_turn_limit: int | None = 50


class PlanSpec(BaseModel):
    plan_id: Literal["free", "pro", "team"]
    title: str
    monthly_turn_limit: int | None
    monthly_price_usd: float
    features: list[str]


class EntitlementStatus(BaseModel):
    learner_id: str
    plan_id: Literal["free", "pro", "team"]
    status: Literal["allowed", "blocked"]
    reason: str
    can_use_voice_loop: bool
    can_use_advanced_history: bool
    turns_used_this_month: int
    turns_limit_this_month: int | None
