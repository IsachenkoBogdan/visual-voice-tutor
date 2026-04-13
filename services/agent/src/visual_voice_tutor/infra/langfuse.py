from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class LangfuseConfig:
    public_key: str
    secret_key: str
    host: str


class LangfuseClient:
    """No-op-ish integration point with structured logs for local runs."""

    def __init__(self, config: LangfuseConfig) -> None:
        self._config = config

    async def start_turn_trace(self, *, session_id: str, turn_id: str, request_id: str) -> None:
        logger.info(
            "langfuse.trace.start",
            session_id=session_id,
            turn_id=turn_id,
            request_id=request_id,
            enabled=bool(self._config.host and self._config.public_key),
        )

    async def add_event(self, *, session_id: str, turn_id: str, name: str, payload: object) -> None:
        logger.info(
            "langfuse.trace.event",
            session_id=session_id,
            turn_id=turn_id,
            name=name,
            payload=payload,
        )

    async def finish_turn_trace(self, *, session_id: str, turn_id: str, status: str) -> None:
        logger.info(
            "langfuse.trace.finish",
            session_id=session_id,
            turn_id=turn_id,
            status=status,
        )
