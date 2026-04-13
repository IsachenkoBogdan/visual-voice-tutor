from __future__ import annotations

import asyncio
import base64
import contextlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from visual_voice_tutor.api.deps import AppContainer
from visual_voice_tutor.api.security import authorize_ws
from visual_voice_tutor.contracts.product import SessionSummaryRecord, UsageEvent
from visual_voice_tutor.contracts.runtime_commands import (
    AsrTranscribeCommand,
    CheckStepCommand,
    InterruptCommand,
    RunMockTurnCommand,
    RuntimeCommand,
)
from visual_voice_tutor.contracts.stream_events import (
    AsrFinalEvent,
    AsrFinalPayload,
    AsrPartialEvent,
    AsrPartialPayload,
    ErrorEvent,
    ErrorPayload,
    InterruptEvent,
    InterruptPayload,
    StatusEvent,
    StatusPayload,
    StreamEvent,
)
from visual_voice_tutor.voice import AsrError

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["runtime"])
runtime_command_adapter: TypeAdapter[RuntimeCommand] = TypeAdapter(RuntimeCommand)


@router.websocket("/ws")
async def runtime_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    container = websocket.app.state.container
    assert isinstance(container, AppContainer)
    if not await authorize_ws(websocket, container.settings):
        return

    send_lock = asyncio.Lock()
    session_id = websocket.query_params.get("session_id", "sess_demo")
    learner_id = websocket.query_params.get("learner_id", "demo_learner")
    user_id = websocket.query_params.get("user_id", "demo_user")

    active_task: asyncio.Task[None] | None = None
    active_cancel_event: asyncio.Event | None = None
    active_turn_id: str | None = None

    async def send_event(event: StreamEvent) -> None:
        async with send_lock:
            await websocket.send_text(event.model_dump_json())
        await container.langfuse.add_event(
            session_id=event.session_id,
            turn_id=event.turn_id,
            name=event.type,
            payload=event.payload.model_dump(mode="json"),
        )

    async def send_error_event(
        *,
        request_id: str,
        turn_id: str,
        code: str,
        message: str,
        retryable: bool,
    ) -> None:
        await send_event(
            ErrorEvent(
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                payload=ErrorPayload(
                    code=code,
                    message=message,
                    retryable=retryable,
                ),
            )
        )

    async def start_turn(command: RunMockTurnCommand | CheckStepCommand) -> None:
        nonlocal active_task, active_cancel_event, active_turn_id

        subscription = await container.product_store.get_subscription(learner_id)
        usage = await container.product_store.list_usage_events(learner_id, limit=1000)
        entitlement = container.entitlement_service.evaluate(
            learner_id=learner_id,
            subscription=subscription,
            usage_events=usage,
        )
        if entitlement.status == "blocked":
            request_id = _new_request_id()
            turn_id = active_turn_id or "turn_blocked"
            await send_event(
                StatusEvent(
                    request_id=request_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    payload=StatusPayload(
                        stage="entitlement_blocked",
                        message=f"Turn blocked: {entitlement.reason}",
                    ),
                )
            )
            await send_error_event(
                request_id=request_id,
                turn_id=turn_id,
                code="entitlement_blocked",
                message=f"Learner is not entitled to start new turn ({entitlement.reason})",
                retryable=False,
            )
            return

        if active_task is not None and not active_task.done():
            request_id = _new_request_id()
            turn_id = active_turn_id or "turn_unknown"
            await send_event(
                StatusEvent(
                    request_id=request_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    payload=StatusPayload(
                        stage="streaming_timeline",
                        message="Turn is already running",
                    ),
                )
            )
            return

        request_id = _new_request_id()
        turn_id = _new_turn_id()
        cancel_event = asyncio.Event()
        active_turn_id = turn_id
        active_cancel_event = cancel_event

        async def run_turn() -> None:
            nonlocal active_task, active_cancel_event, active_turn_id

            turn_started_at = perf_counter()
            utterance_started_at: float | None = None
            await container.langfuse.start_turn_trace(
                session_id=session_id,
                turn_id=turn_id,
                request_id=request_id,
            )

            interrupted = False
            saw_final = False
            try:
                stream: AsyncIterator[StreamEvent]
                if isinstance(command, RunMockTurnCommand):
                    stream = container.orchestrator.stream_mock_turn(
                        session_id=session_id,
                        request_id=request_id,
                        turn_id=turn_id,
                        cancel_event=cancel_event,
                    )
                else:
                    stream = container.orchestrator.stream_check_step(
                        session_id=session_id,
                        request_id=request_id,
                        turn_id=turn_id,
                        payload=command.payload,
                        cancel_event=cancel_event,
                    )

                async for event in stream:
                    if cancel_event.is_set():
                        interrupted = True
                        break
                    if event.type == "final":
                        saw_final = True
                        container.metrics.increment_completed_sessions()
                    await send_event(event)
                    if event.type == "error":
                        container.metrics.increment_tool_errors()
                    if event.type == "status" and event.payload.stage == "tts_degraded":
                        container.metrics.increment_fallback()
                    if event.type == "utterance.start":
                        utterance_started_at = perf_counter()
                    if event.type == "utterance.ready" and utterance_started_at is not None:
                        container.metrics.record_tts_latency((perf_counter() - utterance_started_at) * 1000)
                        utterance_started_at = None
                    if event.type == "final":
                        await container.product_store.append_session_summary(
                            SessionSummaryRecord(
                                session_id=session_id,
                                turn_id=turn_id,
                                learner_id=learner_id,
                                result=event.payload.result,
                                summary=event.payload.summary,
                            )
                        )
                        await container.product_store.append_usage_event(
                            UsageEvent(
                                event_id=f"use_{uuid4().hex[:10]}",
                                learner_id=learner_id,
                                event_type="turn_completed",
                                units=1,
                                session_id=session_id,
                                created_at=datetime.now(UTC),
                            )
                        )
                    await asyncio.sleep(0.02)

                if cancel_event.is_set() and not saw_final:
                    interrupted = True
            except asyncio.CancelledError:
                interrupted = True
                raise
            finally:
                container.metrics.record_request_latency((perf_counter() - turn_started_at) * 1000)
                status = "interrupted" if interrupted else "completed"
                await container.langfuse.finish_turn_trace(
                    session_id=session_id,
                    turn_id=turn_id,
                    status=status,
                )
                active_task = None
                active_cancel_event = None
                active_turn_id = None

        active_task = asyncio.create_task(run_turn())

    async def transcribe_audio(command: AsrTranscribeCommand) -> None:
        started_at = perf_counter()
        request_id = _new_request_id()
        turn_id = active_turn_id or _new_turn_id(prefix="turn_asr")

        await send_event(
            StatusEvent(
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                payload=StatusPayload(
                    stage="asr_transcribing",
                    message="Transcribing student audio chunk",
                ),
            )
        )

        try:
            audio_bytes = base64.b64decode(command.payload.audio_b64, validate=True)
        except Exception:
            await send_error_event(
                request_id=request_id,
                turn_id=turn_id,
                code="invalid_audio_payload",
                message="Incoming ASR payload is not valid base64 audio",
                retryable=False,
            )
            return

        try:
            result = await container.asr_provider.transcribe_chunk(audio_bytes)
        except AsrError as err:
            await send_error_event(
                request_id=request_id,
                turn_id=turn_id,
                code=err.code,
                message=err.message,
                retryable=err.retryable,
            )
            return
        except Exception as exc:  # pragma: no cover - guardrail path
            await send_error_event(
                request_id=request_id,
                turn_id=turn_id,
                code="asr_runtime_failure",
                message=str(exc),
                retryable=True,
            )
            return
        finally:
            container.metrics.record_asr_latency((perf_counter() - started_at) * 1000)

        partial_text = _partial_from_text(result.text)
        if partial_text:
            await send_event(
                AsrPartialEvent(
                    request_id=request_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    payload=AsrPartialPayload(
                        text=partial_text,
                        confidence=max(0.0, min(result.confidence * 0.8, 1.0)),
                    ),
                )
            )

        await send_event(
            AsrFinalEvent(
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                payload=AsrFinalPayload(
                    text=result.text,
                    confidence=result.confidence,
                ),
            )
        )

    async def interrupt_turn(command: InterruptCommand) -> None:
        target_turn_id = command.turn_id or active_turn_id or "turn_unknown"
        if active_cancel_event is not None:
            active_cancel_event.set()

        await send_event(
            InterruptEvent(
                request_id=_new_request_id(),
                session_id=session_id,
                turn_id=target_turn_id,
                payload=InterruptPayload(
                    reason=command.reason,
                    cancel_from_turn_id=target_turn_id,
                ),
            )
        )

    try:
        await container.product_store.link_user_learner(user_id, learner_id)
        state = await container.session_store.load_or_create(session_id)
        state.student_id = learner_id
        await container.session_store.save(state)

        while True:
            message = await websocket.receive_text()
            if not message:
                continue

            command = _parse_runtime_command(message)
            if command is None:
                await send_error_event(
                    request_id=_new_request_id(),
                    turn_id=active_turn_id or "turn_unknown",
                    code="invalid_runtime_command",
                    message="Unknown or malformed runtime command",
                    retryable=False,
                )
                continue

            if isinstance(command, RunMockTurnCommand):
                await start_turn(command)
                continue
            if isinstance(command, CheckStepCommand):
                await start_turn(command)
                continue
            if isinstance(command, AsrTranscribeCommand):
                await transcribe_audio(command)
                continue
            if isinstance(command, InterruptCommand):
                await interrupt_turn(command)
                continue
    except WebSocketDisconnect:
        logger.info("ws.disconnected", session_id=session_id)
    except Exception as exc:  # pragma: no cover - guardrail path
        logger.exception("ws.failure", error=str(exc), session_id=session_id)
        await websocket.close(code=1011)
    finally:
        if active_cancel_event is not None:
            active_cancel_event.set()
        task = active_task
        if task is not None and not task.done():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task


def _parse_runtime_command(message: str) -> RuntimeCommand | None:
    try:
        parsed = runtime_command_adapter.validate_json(message)
    except ValidationError:
        return None
    return parsed


def _new_request_id() -> str:
    return f"req_{uuid4().hex[:10]}"


def _new_turn_id(*, prefix: str = "turn") -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _partial_from_text(text: str) -> str:
    trimmed = text.strip()
    if len(trimmed) <= 5:
        return trimmed
    halfway = max(1, len(trimmed) // 2)
    return trimmed[:halfway].strip()
