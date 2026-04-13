from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from visual_voice_tutor.contracts.product import (
    EntitlementStatus,
    PlanSpec,
    SubscriptionState,
    UsageEvent,
)


@dataclass(slots=True)
class EntitlementService:
    def list_plans(self) -> list[PlanSpec]:
        return [
            PlanSpec(
                plan_id="free",
                title="Free",
                monthly_turn_limit=50,
                monthly_price_usd=0.0,
                features=["check_step", "basic_session_history"],
            ),
            PlanSpec(
                plan_id="pro",
                title="Pro",
                monthly_turn_limit=1500,
                monthly_price_usd=19.0,
                features=["check_step", "voice_loop", "extended_history", "priority_tts"],
            ),
            PlanSpec(
                plan_id="team",
                title="Team",
                monthly_turn_limit=None,
                monthly_price_usd=99.0,
                features=["check_step", "voice_loop", "extended_history", "admin_tools"],
            ),
        ]

    def evaluate(
        self,
        *,
        learner_id: str,
        subscription: SubscriptionState,
        usage_events: list[UsageEvent],
    ) -> EntitlementStatus:
        now = datetime.now(UTC)
        month_ago = now - timedelta(days=30)
        turns_used = sum(
            int(event.units)
            for event in usage_events
            if event.event_type == "turn_completed" and event.created_at >= month_ago
        )

        limit = subscription.monthly_turn_limit
        over_limit = limit is not None and turns_used >= limit
        inactive = subscription.status in {"inactive", "past_due", "canceled"}

        blocked = inactive or over_limit
        reason = "allowed"
        if inactive:
            reason = "subscription_inactive"
        elif over_limit:
            reason = "monthly_turn_limit_exceeded"

        pro_or_team = subscription.plan_id in {"pro", "team"}
        return EntitlementStatus(
            learner_id=learner_id,
            plan_id=subscription.plan_id,
            status="blocked" if blocked else "allowed",
            reason=reason,
            can_use_voice_loop=pro_or_team and not blocked,
            can_use_advanced_history=pro_or_team and not blocked,
            turns_used_this_month=turns_used,
            turns_limit_this_month=limit,
        )
