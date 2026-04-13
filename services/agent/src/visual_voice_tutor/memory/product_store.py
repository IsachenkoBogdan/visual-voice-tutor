from __future__ import annotations

from visual_voice_tutor.contracts.product import (
    AutoEvalRecord,
    HumanEvalRecord,
    LearnerProfile,
    SessionSummaryRecord,
    SubscriptionState,
    UsageEvent,
    UserAccount,
)
from visual_voice_tutor.infra.supabase import SupabaseLearnerBackend


class ProductStore:
    def __init__(self, backend: SupabaseLearnerBackend) -> None:
        self._backend = backend

    async def get_user(self, user_id: str) -> UserAccount:
        raw = await self._backend.get_user_account(user_id)
        return UserAccount.model_validate(raw)

    async def save_user(self, user: UserAccount) -> None:
        await self._backend.upsert_user_account(user.user_id, user.model_dump(mode="json"))

    async def link_user_learner(self, user_id: str, learner_id: str) -> None:
        await self._backend.link_user_learner(user_id, learner_id)

    async def list_user_learners(self, user_id: str) -> list[str]:
        return await self._backend.list_user_learners(user_id)

    async def get_learner_profile(self, learner_id: str) -> LearnerProfile:
        raw = await self._backend.get_learner_profile(learner_id)
        return LearnerProfile.model_validate(raw)

    async def save_learner_profile(self, profile: LearnerProfile) -> None:
        await self._backend.upsert_learner_profile(
            profile.learner_id,
            profile.model_dump(mode="json"),
        )

    async def append_session_summary(self, record: SessionSummaryRecord) -> None:
        await self._backend.append_session_summary(
            record.learner_id,
            record.model_dump(mode="json"),
        )

    async def list_session_summaries(
        self,
        learner_id: str,
        *,
        limit: int = 20,
    ) -> list[SessionSummaryRecord]:
        raw_items = await self._backend.list_session_summaries(learner_id, limit=limit)
        return [SessionSummaryRecord.model_validate(item) for item in raw_items]

    async def get_subscription(self, learner_id: str) -> SubscriptionState:
        raw = await self._backend.get_subscription(learner_id)
        return SubscriptionState.model_validate(raw)

    async def save_subscription(self, subscription: SubscriptionState) -> None:
        await self._backend.upsert_subscription(
            subscription.learner_id,
            subscription.model_dump(mode="json"),
        )

    async def append_usage_event(self, event: UsageEvent) -> None:
        await self._backend.append_usage_event(
            event.learner_id,
            event.model_dump(mode="json"),
        )

    async def list_usage_events(
        self,
        learner_id: str,
        *,
        limit: int = 200,
    ) -> list[UsageEvent]:
        raw_items = await self._backend.list_usage_events(learner_id, limit=limit)
        return [UsageEvent.model_validate(item) for item in raw_items]

    async def save_human_eval(self, record: HumanEvalRecord) -> None:
        await self._backend.insert_human_eval(record.model_dump(mode="json"))

    async def save_auto_eval(self, record: AutoEvalRecord) -> None:
        await self._backend.insert_auto_eval(record.model_dump(mode="json"))
