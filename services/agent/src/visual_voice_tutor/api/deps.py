from __future__ import annotations

from dataclasses import dataclass

from visual_voice_tutor.config import Settings
from visual_voice_tutor.infra import LangfuseClient, MetricsCollector
from visual_voice_tutor.memory import ProductStore, RedisSessionStore, SupabaseLearnerStore
from visual_voice_tutor.orchestrator import EntitlementService, TutorOrchestrator
from visual_voice_tutor.orchestrator.checker import HybridJudgeService
from visual_voice_tutor.voice import AsrProvider


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    orchestrator: TutorOrchestrator
    langfuse: LangfuseClient
    metrics: MetricsCollector
    session_store: RedisSessionStore
    learner_store: SupabaseLearnerStore
    product_store: ProductStore
    entitlement_service: EntitlementService
    judge_service: HybridJudgeService
    asr_provider: AsrProvider
