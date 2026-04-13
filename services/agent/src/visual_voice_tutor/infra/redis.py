from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy


class RedisSessionBackend:
    """In-memory stub that preserves Redis-like async API surface."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._sessions: dict[str, dict[str, object]] = {}

    async def get_session(self, session_id: str) -> dict[str, object] | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return deepcopy(session)

    async def set_session(self, session_id: str, payload: Mapping[str, object]) -> None:
        self._sessions[session_id] = deepcopy(dict(payload))
