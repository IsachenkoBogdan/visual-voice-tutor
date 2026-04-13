from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from visual_voice_tutor.config.settings import Settings


def bootstrap_telemetry(settings: Settings) -> TracerProvider:
    """Initialize OpenTelemetry tracer provider.

    Exporters are intentionally not wired yet to keep local setup simple while preserving
    instrumentation boundaries.
    """

    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        return current_provider

    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.otel_service_name})
    )
    trace.set_tracer_provider(provider)
    return provider
