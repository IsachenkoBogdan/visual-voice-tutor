from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from visual_voice_tutor.config.settings import Settings
from visual_voice_tutor.contracts.runtime_commands import BoardShapeSnapshot, CheckStepPayload
from visual_voice_tutor.contracts.stream_events import (
    AnchorTiming,
    CheckQuestionEvent,
    FinalEvent,
    StreamEvent,
    UtteranceAudioChunkEvent,
    UtteranceAudioEndEvent,
    UtteranceReadyEvent,
)
from visual_voice_tutor.contracts.whiteboard import Bounds
from visual_voice_tutor.infra.redis import RedisSessionBackend
from visual_voice_tutor.infra.supabase import SupabaseLearnerBackend
from visual_voice_tutor.main import create_app
from visual_voice_tutor.memory import RedisSessionStore, SupabaseLearnerStore
from visual_voice_tutor.orchestrator.checker import HybridJudgeService
from visual_voice_tutor.orchestrator.service import TutorOrchestrator
from visual_voice_tutor.voice.tts_provider import (
    TtsAudioFormat,
    TtsProvider,
    TtsSynthesisError,
    TtsSynthesisResult,
)


class SuccessTtsProvider(TtsProvider):
    async def synthesize(
        self, *, utterance_id: str, text: str, anchor_names: list[str]
    ) -> TtsSynthesisResult:
        anchors = [
            AnchorTiming(anchor_id=f"a{idx+1}", name=name, time_ms=idx * 500)
            for idx, name in enumerate(anchor_names)
        ]
        audio_bytes = b"0" * 50000
        return TtsSynthesisResult(
            utterance_id=utterance_id,
            audio_id=f"audio_{utterance_id}",
            duration_ms=2400,
            anchors=anchors,
            audio_bytes=audio_bytes,
            audio_format=TtsAudioFormat(
                encoding="mp3",
                sample_rate_hz=24_000,
                channels=1,
                mime_type="audio/mpeg",
            ),
        )


class FailingTtsProvider(TtsProvider):
    async def synthesize(
        self, *, utterance_id: str, text: str, anchor_names: list[str]
    ) -> TtsSynthesisResult:
        raise TtsSynthesisError(
            code="azure_tts_not_configured",
            message="Azure Speech credentials are not configured",
            retryable=False,
        )


def _build_orchestrator(provider: TtsProvider, *, chunk_size: int = 8192) -> TutorOrchestrator:
    session_store = RedisSessionStore(RedisSessionBackend("redis://localhost:6379/0"))
    learner_store = SupabaseLearnerStore(SupabaseLearnerBackend("", ""))
    return TutorOrchestrator(
        tts_provider=provider,
        session_store=session_store,
        learner_store=learner_store,
        judge_service=HybridJudgeService(Settings()),
        tts_chunk_size_bytes=chunk_size,
    )


async def _collect_events(stream: AsyncIterator[StreamEvent]) -> list[StreamEvent]:
    events: list[StreamEvent] = []
    async for event in stream:
        events.append(event)
    return events


def _types(events: list[StreamEvent]) -> list[str]:
    return [event.type for event in events]


def _check_payload(*, recognized_text: str | None) -> CheckStepPayload:
    return CheckStepPayload(
        problem_text="Реши уравнение 3(x+2)=15",
        expected_step="3x+6=15",
        recognized_text=recognized_text,
        active_region_bounds=Bounds(x=110, y=90, w=260, h=120),
        relevant_shapes=[
            BoardShapeSnapshot(
                id="shape_1",
                type="text",
                x=120,
                y=115,
                w=140,
                h=28,
                text=recognized_text,
                author="student",
                semantic_tag="student_current_line",
            )
        ],
    )


@pytest.mark.asyncio
async def test_orchestrator_success_streams_chunked_audio() -> None:
    orchestrator = _build_orchestrator(SuccessTtsProvider(), chunk_size=4096)

    events = await _collect_events(
        orchestrator.stream_mock_turn(
            session_id="s1",
            request_id="r1",
            turn_id="turn_test_1",
        )
    )

    event_types = _types(events)
    assert event_types[:4] == ["status", "status", "utterance.start", "utterance.ready"]
    assert "utterance.audio.chunk" in event_types
    assert "utterance.audio.end" in event_types
    assert "error" not in event_types
    assert event_types[-1] == "final"

    ready = next(event for event in events if isinstance(event, UtteranceReadyEvent))
    assert ready.payload.has_audio is True

    chunks = [event for event in events if isinstance(event, UtteranceAudioChunkEvent)]
    seqs = [event.payload.seq for event in chunks]
    assert seqs == list(range(len(seqs)))

    audio_end = next(event for event in events if isinstance(event, UtteranceAudioEndEvent))
    assert audio_end.payload.total_chunks == len(chunks)
    assert audio_end.payload.total_bytes == sum(event.payload.chunk_size_bytes for event in chunks)


@pytest.mark.asyncio
async def test_orchestrator_fallback_keeps_board_and_final() -> None:
    orchestrator = _build_orchestrator(FailingTtsProvider())

    events = await _collect_events(
        orchestrator.stream_mock_turn(
            session_id="s2",
            request_id="r2",
            turn_id="turn_test_2",
        )
    )

    event_types = _types(events)
    assert event_types[:4] == ["status", "status", "utterance.start", "utterance.ready"]
    assert "status" in event_types
    assert "error" in event_types
    assert "utterance.audio.chunk" not in event_types
    assert "utterance.audio.end" in event_types
    assert event_types[-1] == "final"

    ready = next(event for event in events if isinstance(event, UtteranceReadyEvent))
    assert ready.payload.has_audio is False
    assert ready.payload.fallback_reason is not None

    board_actions = [event for event in events if event.type == "board.action"]
    assert len(board_actions) == 3


@pytest.mark.asyncio
async def test_orchestrator_interrupt_stops_before_final() -> None:
    orchestrator = _build_orchestrator(SuccessTtsProvider())
    cancel_event = asyncio.Event()

    events: list[StreamEvent] = []
    async for event in orchestrator.stream_mock_turn(
        session_id="s3",
        request_id="r3",
        turn_id="turn_test_3",
        cancel_event=cancel_event,
    ):
        events.append(event)
        if event.type == "utterance.start":
            cancel_event.set()

    event_types = _types(events)
    assert event_types == ["status", "status", "utterance.start"]
    assert "final" not in event_types


def test_api_health_and_ws_interrupt_smoke() -> None:
    app = create_app()
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        with client.websocket_connect("/ws?session_id=ws_test") as ws:
            ws.send_json({"type": "run_mock_turn"})
            first = ws.receive_json()
            turn_id = first["turn_id"]

            ws.send_json(
                {
                    "type": "interrupt",
                    "turn_id": turn_id,
                    "reason": "test_interrupt",
                }
            )

            got_interrupt = False
            for _ in range(8):
                message = ws.receive_json()
                if message.get("type") == "interrupt":
                    got_interrupt = True
                    break

            assert got_interrupt is True


def test_ws_stream_contains_chunk_events_with_success_provider() -> None:
    app = create_app()
    app.state.container.orchestrator._tts_provider = SuccessTtsProvider()  # type: ignore[attr-defined]
    app.state.container.orchestrator._tts_chunk_size_bytes = 2048  # type: ignore[attr-defined]

    with TestClient(app) as client, client.websocket_connect("/ws?session_id=ws_chunks") as ws:
        ws.send_json({"type": "run_mock_turn"})
        event_types: list[str] = []
        while True:
            message = ws.receive_json()
            event_types.append(message["type"])
            if message["type"] == "final":
                break

        assert "utterance.audio.chunk" in event_types
        assert "utterance.audio.end" in event_types


@pytest.mark.asyncio
async def test_orchestrator_check_step_success_path() -> None:
    orchestrator = _build_orchestrator(SuccessTtsProvider(), chunk_size=4096)
    payload = _check_payload(recognized_text="3x+6=15")

    events = await _collect_events(
        orchestrator.stream_check_step(
            session_id="s4",
            request_id="r4",
            turn_id="turn_test_4",
            payload=payload,
        )
    )

    event_types = _types(events)
    assert event_types[:2] == ["status", "status"]
    assert "board.action" in event_types
    assert "check.question" in event_types
    assert event_types[-1] == "final"

    final = next(event for event in events if isinstance(event, FinalEvent))
    assert final.payload.result == "ok"

    question = next(event for event in events if isinstance(event, CheckQuestionEvent))
    assert question.payload.question


@pytest.mark.asyncio
async def test_orchestrator_check_step_tts_failure_degrades_to_text_board() -> None:
    orchestrator = _build_orchestrator(FailingTtsProvider())
    payload = _check_payload(recognized_text="3x+8=15")

    events = await _collect_events(
        orchestrator.stream_check_step(
            session_id="s5",
            request_id="r5",
            turn_id="turn_test_5",
            payload=payload,
        )
    )

    event_types = _types(events)
    assert "error" in event_types
    assert "board.action" in event_types
    assert event_types[-1] == "final"

    final = next(event for event in events if isinstance(event, FinalEvent))
    assert final.payload.result == "needs_reexplanation"


def test_ws_check_step_command_emits_final() -> None:
    app = create_app()
    app.state.container.orchestrator._tts_provider = SuccessTtsProvider()  # type: ignore[attr-defined]

    with TestClient(app) as client, client.websocket_connect("/ws?session_id=ws_check_step") as ws:
        ws.send_json(
            {
                "type": "check_step",
                "payload": _check_payload(recognized_text="3x+8=15").model_dump(mode="json"),
            }
        )

        event_types: list[str] = []
        while True:
            message = ws.receive_json()
            event_types.append(message["type"])
            if message["type"] == "final":
                break

        assert "board.action" in event_types
        assert "check.question" in event_types
