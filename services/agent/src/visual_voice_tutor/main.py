from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from visual_voice_tutor.api import health_router, product_router, ws_router
from visual_voice_tutor.api.deps import AppContainer
from visual_voice_tutor.config import configure_logging, get_settings
from visual_voice_tutor.infra import (
    LangfuseClient,
    LangfuseConfig,
    MetricsCollector,
    RedisSessionBackend,
    SupabaseLearnerBackend,
    bootstrap_telemetry,
)
from visual_voice_tutor.memory import ProductStore, RedisSessionStore, SupabaseLearnerStore
from visual_voice_tutor.orchestrator import EntitlementService, TutorOrchestrator
from visual_voice_tutor.orchestrator.checker import HybridJudgeService
from visual_voice_tutor.voice import AzureAsrProvider, AzureTtsProvider


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging(settings.log_level)
    bootstrap_telemetry(settings)

    redis_backend = RedisSessionBackend(settings.redis_url)
    supabase_backend = SupabaseLearnerBackend(
        settings.supabase_url, settings.supabase_service_role_key
    )

    session_store = RedisSessionStore(redis_backend)
    learner_store = SupabaseLearnerStore(supabase_backend)
    product_store = ProductStore(supabase_backend)
    entitlement_service = EntitlementService()
    judge_service = HybridJudgeService(settings)
    asr_provider = AzureAsrProvider(
        speech_key=settings.azure_speech_key,
        speech_region=settings.azure_speech_region,
        language=settings.azure_asr_language,
        timeout_sec=settings.azure_asr_timeout_sec,
    )

    orchestrator = TutorOrchestrator(
        tts_provider=AzureTtsProvider(
            speech_key=settings.azure_speech_key,
            speech_region=settings.azure_speech_region,
            voice_name=settings.azure_tts_voice,
            output_format=settings.azure_tts_output_format,
            request_timeout_sec=settings.azure_tts_request_timeout_sec,
        ),
        session_store=session_store,
        learner_store=learner_store,
        judge_service=judge_service,
        tts_chunk_size_bytes=settings.azure_tts_chunk_size_bytes,
    )

    langfuse = LangfuseClient(
        LangfuseConfig(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    )

    container = AppContainer(
        settings=settings,
        orchestrator=orchestrator,
        langfuse=langfuse,
        metrics=MetricsCollector(),
        session_store=session_store,
        learner_store=learner_store,
        product_store=product_store,
        entitlement_service=entitlement_service,
        judge_service=judge_service,
        asr_provider=asr_provider,
    )

    app = FastAPI(title=settings.app_name)
    app.state.container = container
    origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(ws_router)
    app.include_router(product_router)
    return app


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "visual_voice_tutor.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    main()
