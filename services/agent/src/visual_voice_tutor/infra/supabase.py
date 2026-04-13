from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any


class SupabaseLearnerBackend:
    """In-memory stub for future Supabase integration.

    Keeps API surface close to real storage contracts so runtime layers can stay stable.
    """

    def __init__(self, url: str, service_role_key: str) -> None:
        self.url = url
        self.service_role_key = service_role_key
        self._memory: dict[str, dict[str, object]] = {}
        self._profiles: dict[str, dict[str, object]] = {}
        self._sessions: dict[str, list[dict[str, object]]] = defaultdict(list)
        self._users: dict[str, dict[str, object]] = {}
        self._user_learners: dict[str, set[str]] = defaultdict(set)
        self._subscriptions: dict[str, dict[str, object]] = {}
        self._usage_events: dict[str, list[dict[str, object]]] = defaultdict(list)
        self._human_evals: list[dict[str, object]] = []
        self._auto_evals: list[dict[str, object]] = []

    async def get_learner_memory(self, learner_id: str) -> dict[str, object]:
        data = self._memory.get(learner_id)
        if data is None:
            return {
                "recurring_mistakes": ["distribution_errors"],
                "pace_preference": "slow",
                "recent_outcomes": ["needs_reexplanation"],
            }
        return deepcopy(data)

    async def upsert_learner_memory(self, learner_id: str, memory: dict[str, object]) -> None:
        self._memory[learner_id] = deepcopy(memory)

    async def get_learner_profile(self, learner_id: str) -> dict[str, object]:
        profile = self._profiles.get(learner_id)
        if profile is None:
            return {
                "learner_id": learner_id,
                "display_name": learner_id,
                "grade_band": "4-7",
                "pace_preference": "neutral",
                "weak_spots": ["linear_equations"],
                "recurring_mistakes": ["distribution_errors"],
                "recent_topics": ["linear_equations"],
            }
        return deepcopy(profile)

    async def upsert_learner_profile(self, learner_id: str, profile: dict[str, object]) -> None:
        self._profiles[learner_id] = deepcopy(profile)

    async def append_session_summary(self, learner_id: str, summary: dict[str, object]) -> None:
        self._sessions[learner_id].append(deepcopy(summary))

    async def list_session_summaries(
        self,
        learner_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        records = self._sessions.get(learner_id, [])
        return [deepcopy(item) for item in records[-limit:]][::-1]

    async def get_user_account(self, user_id: str) -> dict[str, object]:
        user = self._users.get(user_id)
        if user is None:
            return {
                "user_id": user_id,
                "email": f"{user_id}@example.local",
                "role": "parent",
                "learner_ids": sorted(self._user_learners.get(user_id, set())),
            }
        hydrated = deepcopy(user)
        hydrated["learner_ids"] = sorted(self._user_learners.get(user_id, set()))
        return hydrated

    async def upsert_user_account(self, user_id: str, account: dict[str, object]) -> None:
        self._users[user_id] = deepcopy(account)

    async def link_user_learner(self, user_id: str, learner_id: str) -> None:
        self._user_learners[user_id].add(learner_id)

    async def list_user_learners(self, user_id: str) -> list[str]:
        return sorted(self._user_learners.get(user_id, set()))

    async def get_subscription(self, learner_id: str) -> dict[str, object]:
        sub = self._subscriptions.get(learner_id)
        if sub is None:
            return {
                "learner_id": learner_id,
                "plan_id": "free",
                "status": "active",
                "renews_at": None,
                "monthly_turn_limit": 50,
            }
        return deepcopy(sub)

    async def upsert_subscription(self, learner_id: str, subscription: dict[str, object]) -> None:
        self._subscriptions[learner_id] = deepcopy(subscription)

    async def append_usage_event(self, learner_id: str, event: dict[str, object]) -> None:
        self._usage_events[learner_id].append(deepcopy(event))

    async def list_usage_events(
        self,
        learner_id: str,
        *,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        events = self._usage_events.get(learner_id, [])
        return [deepcopy(item) for item in events[-limit:]]

    async def insert_human_eval(self, payload: dict[str, Any]) -> None:
        self._human_evals.append(deepcopy(payload))

    async def insert_auto_eval(self, payload: dict[str, Any]) -> None:
        self._auto_evals.append(deepcopy(payload))
