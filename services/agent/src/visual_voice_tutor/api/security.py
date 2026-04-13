from __future__ import annotations

from fastapi import HTTPException, Request, WebSocket

from visual_voice_tutor.config import Settings


def authorize_http(request: Request, settings: Settings) -> None:
    if not settings.api_auth_enabled:
        return

    token = _extract_http_token(request)
    if token and token == settings.api_auth_token:
        return

    raise HTTPException(status_code=401, detail="Unauthorized")


async def authorize_ws(websocket: WebSocket, settings: Settings) -> bool:
    if not settings.api_auth_enabled:
        return True

    token = _extract_ws_token(websocket)
    if token and token == settings.api_auth_token:
        return True

    await websocket.close(code=4401, reason="Unauthorized")
    return False


def _extract_http_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if header and header.lower().startswith("bearer "):
        return header[7:].strip()
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key.strip()
    query_key = request.query_params.get("api_key")
    if query_key:
        return query_key.strip()
    return None


def _extract_ws_token(websocket: WebSocket) -> str | None:
    header = websocket.headers.get("authorization")
    if header and header.lower().startswith("bearer "):
        return header[7:].strip()
    api_key = websocket.headers.get("x-api-key")
    if api_key:
        return api_key.strip()
    query_key = websocket.query_params.get("api_key")
    if query_key:
        return query_key.strip()
    return None
