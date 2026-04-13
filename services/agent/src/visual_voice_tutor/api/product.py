from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request

from visual_voice_tutor.api.deps import AppContainer
from visual_voice_tutor.api.security import authorize_http
from visual_voice_tutor.contracts.product import (
    AutoEvalRecord,
    EntitlementStatus,
    HumanEvalRecord,
    LearnerProfile,
    PlanSpec,
    SessionSummaryRecord,
    SubscriptionState,
    UsageEvent,
    UserAccount,
)
from visual_voice_tutor.evals import list_eval_datasets

router = APIRouter(prefix="/api/v1", tags=["product"])


def _container(request: Request) -> AppContainer:
    container = request.app.state.container
    if not isinstance(container, AppContainer):
        raise HTTPException(status_code=500, detail="Application container not configured")
    authorize_http(request, container.settings)
    return container


@router.get("/accounts/{user_id}", response_model=UserAccount)
async def get_account(user_id: str, request: Request) -> UserAccount:
    container = _container(request)
    return await container.product_store.get_user(user_id)


@router.put("/accounts/{user_id}/learners/{learner_id}")
async def link_user_learner(user_id: str, learner_id: str, request: Request) -> dict[str, str]:
    container = _container(request)
    await container.product_store.link_user_learner(user_id, learner_id)
    return {"status": "linked"}


@router.get("/accounts/{user_id}/learners", response_model=list[LearnerProfile])
async def list_account_learners(user_id: str, request: Request) -> list[LearnerProfile]:
    container = _container(request)
    learner_ids = await container.product_store.list_user_learners(user_id)
    return [await container.product_store.get_learner_profile(learner_id) for learner_id in learner_ids]


@router.get("/learners/{learner_id}", response_model=LearnerProfile)
async def get_learner_profile(learner_id: str, request: Request) -> LearnerProfile:
    container = _container(request)
    return await container.product_store.get_learner_profile(learner_id)


@router.put("/learners/{learner_id}", response_model=LearnerProfile)
async def update_learner_profile(
    learner_id: str,
    payload: LearnerProfile,
    request: Request,
) -> LearnerProfile:
    if payload.learner_id != learner_id:
        raise HTTPException(status_code=400, detail="learner_id mismatch")
    container = _container(request)
    await container.product_store.save_learner_profile(payload)
    return payload


@router.get("/learners/{learner_id}/sessions", response_model=list[SessionSummaryRecord])
async def list_learner_sessions(
    learner_id: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SessionSummaryRecord]:
    container = _container(request)
    return await container.product_store.list_session_summaries(learner_id, limit=limit)


@router.post("/evals/human", response_model=HumanEvalRecord)
async def submit_human_eval(payload: HumanEvalRecord, request: Request) -> HumanEvalRecord:
    container = _container(request)
    await container.product_store.save_human_eval(payload)
    return payload


@router.post("/evals/auto", response_model=AutoEvalRecord)
async def submit_auto_eval(payload: AutoEvalRecord, request: Request) -> AutoEvalRecord:
    container = _container(request)
    await container.product_store.save_auto_eval(payload)
    return payload


@router.get("/evals/datasets", response_model=list[str])
async def get_eval_datasets() -> list[str]:
    return list_eval_datasets()


@router.get("/billing/plans", response_model=list[PlanSpec])
async def list_plans(request: Request) -> list[PlanSpec]:
    container = _container(request)
    return container.entitlement_service.list_plans()


@router.get("/billing/subscription/{learner_id}", response_model=SubscriptionState)
async def get_subscription(learner_id: str, request: Request) -> SubscriptionState:
    container = _container(request)
    return await container.product_store.get_subscription(learner_id)


@router.put("/billing/subscription/{learner_id}", response_model=SubscriptionState)
async def set_subscription(
    learner_id: str,
    payload: SubscriptionState,
    request: Request,
) -> SubscriptionState:
    if payload.learner_id != learner_id:
        raise HTTPException(status_code=400, detail="learner_id mismatch")
    container = _container(request)
    await container.product_store.save_subscription(payload)
    return payload


@router.get("/billing/usage/{learner_id}", response_model=list[UsageEvent])
async def list_usage(
    learner_id: str,
    request: Request,
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[UsageEvent]:
    container = _container(request)
    return await container.product_store.list_usage_events(learner_id, limit=limit)


@router.post("/billing/usage/{learner_id}", response_model=UsageEvent)
async def add_usage_event(
    learner_id: str,
    request: Request,
    event_type: Literal["turn_completed", "asr_minute", "tts_characters"] = Query(
        default="turn_completed"
    ),
    units: float = Query(default=1.0, gt=0.0),
) -> UsageEvent:
    event = UsageEvent(
        event_id=f"use_{uuid4().hex[:10]}",
        learner_id=learner_id,
        event_type=event_type,
        units=units,
        created_at=datetime.now(UTC),
    )
    container = _container(request)
    await container.product_store.append_usage_event(event)
    return event


@router.get("/billing/entitlement/{learner_id}", response_model=EntitlementStatus)
async def get_entitlement(learner_id: str, request: Request) -> EntitlementStatus:
    container = _container(request)
    subscription = await container.product_store.get_subscription(learner_id)
    usage = await container.product_store.list_usage_events(learner_id, limit=1000)
    return container.entitlement_service.evaluate(
        learner_id=learner_id,
        subscription=subscription,
        usage_events=usage,
    )


@router.get("/ops/metrics")
async def get_metrics_snapshot(request: Request) -> dict[str, float | int]:
    container = _container(request)
    return container.metrics.snapshot()
