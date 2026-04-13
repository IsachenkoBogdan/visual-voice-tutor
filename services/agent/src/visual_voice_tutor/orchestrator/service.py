from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncIterator
from dataclasses import dataclass

from visual_voice_tutor.board import build_context_from_check_request, build_mock_context
from visual_voice_tutor.contracts.judge import JudgeResponse
from visual_voice_tutor.contracts.runtime_commands import CheckStepPayload
from visual_voice_tutor.contracts.stream_events import (
    AnchorTiming,
    BoardActionEvent,
    BoardBatchDoneEvent,
    BoardBatchDonePayload,
    CheckQuestionEvent,
    CheckQuestionPayload,
    ErrorEvent,
    ErrorPayload,
    FinalEvent,
    FinalPayload,
    StatusEvent,
    StatusPayload,
    StreamEvent,
    UtteranceAudioChunkEvent,
    UtteranceAudioChunkPayload,
    UtteranceAudioEndEvent,
    UtteranceAudioEndPayload,
    UtteranceReadyEvent,
    UtteranceReadyPayload,
    UtteranceStartEvent,
    UtteranceStartPayload,
)
from visual_voice_tutor.contracts.whiteboard import (
    Bounds,
    CreateTextAction,
    FocusRegionAction,
    HighlightRegionAction,
    PlannedBoardAction,
    PulseRegionAction,
    ScheduleAnchor,
    ScheduleAtStart,
)
from visual_voice_tutor.memory import RedisSessionStore, SupabaseLearnerStore
from visual_voice_tutor.memory.summary_service import build_session_summary
from visual_voice_tutor.orchestrator.checker import HybridJudgeService
from visual_voice_tutor.orchestrator.state_machine import OrchestratorStateMachine, TurnStage
from visual_voice_tutor.orchestrator.types import TutoringStep
from visual_voice_tutor.sync import validate_actions, with_resolved_timing
from visual_voice_tutor.voice import TtsAudioFormat, TtsProvider, TtsSynthesisError


@dataclass(slots=True)
class AudioTransportState:
    has_audio: bool
    format: TtsAudioFormat
    audio_bytes: bytes
    anchors: list[AnchorTiming]
    duration_ms: int
    fallback_reason: str | None
    error: TtsSynthesisError | None


class TutorOrchestrator:
    """Custom latency-oriented orchestration layer for the live tutoring loop."""

    def __init__(
        self,
        *,
        tts_provider: TtsProvider,
        session_store: RedisSessionStore,
        learner_store: SupabaseLearnerStore,
        judge_service: HybridJudgeService,
        tts_chunk_size_bytes: int,
    ) -> None:
        self._tts_provider = tts_provider
        self._session_store = session_store
        self._learner_store = learner_store
        self._judge_service = judge_service
        self._tts_chunk_size_bytes = max(1024, tts_chunk_size_bytes)

    async def stream_mock_turn(
        self,
        *,
        session_id: str,
        request_id: str,
        turn_id: str,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[StreamEvent]:
        machine = OrchestratorStateMachine()

        def cancelled() -> bool:
            return bool(cancel_event and cancel_event.is_set())

        yield StatusEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=StatusPayload(
                stage=machine.stage,
                message="Analyzing recent student work",
            ),
        )
        if cancelled():
            return

        state = await self._session_store.load_or_create(session_id)
        learner = await self._learner_store.get(state.student_id or "demo_learner")
        build_mock_context(learner_memory=learner)

        machine.advance(TurnStage.PLANNING_STEP)
        step = self._build_mock_step(turn_id=turn_id)
        judge = JudgeResponse(
            recognized_content="3x+8=15",
            is_legible=True,
            is_correct=False,
            confidence=0.89,
            error_type="distribution_error",
            teacher_response_mode="give_small_hint",
            next_hint="Проверь, на что умножается число 2 внутри скобок.",
        )
        summary = build_session_summary(step, judge)

        async for event in self._stream_step(
            machine=machine,
            session_id=session_id,
            request_id=request_id,
            turn_id=turn_id,
            step=step,
            judge=judge,
            summary=summary,
            cancel_event=cancel_event,
        ):
            yield event

    async def stream_check_step(
        self,
        *,
        session_id: str,
        request_id: str,
        turn_id: str,
        payload: CheckStepPayload,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[StreamEvent]:
        machine = OrchestratorStateMachine()

        def cancelled() -> bool:
            return bool(cancel_event and cancel_event.is_set())

        yield StatusEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=StatusPayload(
                stage=machine.stage,
                message="Building board-aware context package",
            ),
        )
        if cancelled():
            return

        state = await self._session_store.load_or_create(session_id)
        learner = await self._learner_store.get(state.student_id or "demo_learner")
        context = build_context_from_check_request(payload=payload, learner_memory=learner)

        machine.advance(TurnStage.PLANNING_STEP)
        yield StatusEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=StatusPayload(
                stage=machine.stage,
                message="Evaluating current student step",
            ),
        )
        if cancelled():
            return

        judge, judge_meta = await self._judge_service.evaluate(context)
        step = self._build_check_step(turn_id=turn_id, payload=payload, judge=judge)
        summary = build_session_summary(step, judge)
        if judge_meta.source != "deterministic":
            summary = f"{summary} Source: {judge_meta.source}."

        async for event in self._stream_step(
            machine=machine,
            session_id=session_id,
            request_id=request_id,
            turn_id=turn_id,
            step=step,
            judge=judge,
            summary=summary,
            cancel_event=cancel_event,
        ):
            yield event

    async def _stream_step(
        self,
        *,
        machine: OrchestratorStateMachine,
        session_id: str,
        request_id: str,
        turn_id: str,
        step: TutoringStep,
        judge: JudgeResponse,
        summary: str,
        cancel_event: asyncio.Event | None,
    ) -> AsyncIterator[StreamEvent]:
        def cancelled() -> bool:
            return bool(cancel_event and cancel_event.is_set())

        machine.advance(TurnStage.SYNTHESIZING_TTS)
        yield StatusEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=StatusPayload(
                stage=machine.stage,
                message="Synthesizing Russian narration with Azure TTS",
            ),
        )
        if cancelled():
            return

        utterance_id = f"utt_{turn_id}"
        yield UtteranceStartEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=UtteranceStartPayload(
                utterance_id=utterance_id,
                text=step.narration,
                audio_id=f"audio_{utterance_id}",
            ),
        )
        if cancelled():
            return

        audio_state = await self._synthesize_audio(
            utterance_id=utterance_id,
            text=step.narration,
            anchor_names=step.anchor_names,
        )

        anchors = _resolve_anchor_timings(
            step=step,
            fallback_duration_ms=max(2_000, len(step.narration) * 30),
            explicit_audio_anchor_ms=audio_state.duration_ms if audio_state.has_audio else None,
            provider_anchors=audio_state.anchors,
        )
        duration_ms = _resolve_duration_ms(audio_state, anchors, step.narration)

        yield UtteranceReadyEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=UtteranceReadyPayload(
                utterance_id=utterance_id,
                duration_ms=duration_ms,
                anchors=anchors,
                encoding=audio_state.format.encoding,
                sample_rate_hz=audio_state.format.sample_rate_hz,
                channels=audio_state.format.channels,
                has_audio=audio_state.has_audio,
                fallback_reason=audio_state.fallback_reason,
            ),
        )
        if cancelled():
            return

        if audio_state.error is not None:
            yield StatusEvent(
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                payload=StatusPayload(
                    stage="tts_degraded",
                    message="Azure TTS unavailable, continuing with text+board fallback",
                ),
            )
            yield ErrorEvent(
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                payload=ErrorPayload(
                    code=audio_state.error.code,
                    message=audio_state.error.message,
                    retryable=audio_state.error.retryable,
                ),
            )

        total_chunks = 0
        if audio_state.has_audio:
            for seq, chunk in _chunk_audio_bytes(
                audio_state.audio_bytes,
                chunk_size=self._tts_chunk_size_bytes,
            ):
                if cancelled():
                    return

                yield UtteranceAudioChunkEvent(
                    request_id=request_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    payload=UtteranceAudioChunkPayload(
                        utterance_id=utterance_id,
                        seq=seq,
                        chunk_b64=base64.b64encode(chunk).decode("ascii"),
                        chunk_size_bytes=len(chunk),
                        encoding=audio_state.format.encoding,
                        sample_rate_hz=audio_state.format.sample_rate_hz,
                        channels=audio_state.format.channels,
                    ),
                )
                total_chunks += 1

        yield UtteranceAudioEndEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=UtteranceAudioEndPayload(
                utterance_id=utterance_id,
                total_chunks=total_chunks,
                total_bytes=len(audio_state.audio_bytes),
            ),
        )
        if cancelled():
            return

        machine.advance(TurnStage.STREAMING_TIMELINE)
        validated_actions = validate_actions(step.board_actions)
        for action, _ms in with_resolved_timing(
            validated_actions,
            anchors=anchors,
            duration_ms=duration_ms,
        ):
            if cancelled():
                return
            yield BoardActionEvent(
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                payload=action,
            )

        if cancelled():
            return

        yield BoardBatchDoneEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=BoardBatchDonePayload(batch_id="batch_1", step_id=step.step_id),
        )
        yield CheckQuestionEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=CheckQuestionPayload(question=step.check_question),
        )

        state = await self._session_store.load_or_create(session_id)
        learner = await self._learner_store.get(state.student_id or "demo_learner")

        state.dialog_history.append(step.narration)
        state.last_canvas_actions = [action.action_id for action in validated_actions]
        state.last_spoken_hint = judge.next_hint
        state.completion_status = step.final_result
        await self._session_store.save(state)

        learner.recent_outcomes.append(step.final_result)
        await self._learner_store.put(state.student_id or "demo_learner", learner)

        machine.advance(TurnStage.COMPLETED)
        yield FinalEvent(
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            payload=FinalPayload(result=step.final_result, summary=summary),
        )

    async def _synthesize_audio(
        self,
        *,
        utterance_id: str,
        text: str,
        anchor_names: list[str],
    ) -> AudioTransportState:
        try:
            tts_result = await self._tts_provider.synthesize(
                utterance_id=utterance_id,
                text=text,
                anchor_names=anchor_names,
            )
            has_audio = len(tts_result.audio_bytes) > 0
            return AudioTransportState(
                has_audio=has_audio,
                format=tts_result.audio_format,
                audio_bytes=tts_result.audio_bytes,
                anchors=tts_result.anchors,
                duration_ms=tts_result.duration_ms,
                fallback_reason=None if has_audio else "empty_audio_payload",
                error=None
                if has_audio
                else TtsSynthesisError(
                    code="azure_tts_empty_audio",
                    message="Azure TTS returned empty audio payload",
                    retryable=True,
                ),
            )
        except TtsSynthesisError as err:
            return AudioTransportState(
                has_audio=False,
                format=TtsAudioFormat(
                    encoding="mp3",
                    sample_rate_hz=24_000,
                    channels=1,
                    mime_type="audio/mpeg",
                ),
                audio_bytes=b"",
                anchors=[],
                duration_ms=0,
                fallback_reason=err.message,
                error=err,
            )

    def _build_mock_step(self, *, turn_id: str) -> TutoringStep:
        step_suffix = turn_id.replace("turn_", "")
        return TutoringStep(
            step_id="step_1",
            narration=(
                "Сначала покажем исходное уравнение. "
                "Теперь раскроем скобки аккуратно: тройка умножается и на икс, и на два."
            ),
            anchor_names=["show_equation", "highlight_brackets", "write_next_line"],
            board_actions=[
                PlannedBoardAction(
                    action_id=f"act_1_{step_suffix}",
                    schedule=ScheduleAtStart(),
                    action=CreateTextAction(
                        shape_id=f"eq_1_{step_suffix}",
                        x=120,
                        y=90,
                        text="3(x+2)=15",
                    ),
                ),
                PlannedBoardAction(
                    action_id=f"act_2_{step_suffix}",
                    schedule=ScheduleAnchor(anchor_id="a2", offset_ms=0),
                    action=HighlightRegionAction(
                        region_id="brackets_region",
                        bounds=Bounds(x=150, y=85, w=70, h=36),
                        label="Скобки",
                    ),
                ),
                PlannedBoardAction(
                    action_id=f"act_3_{step_suffix}",
                    schedule=ScheduleAnchor(anchor_id="a3", offset_ms=70),
                    action=CreateTextAction(
                        shape_id=f"eq_2_{step_suffix}",
                        x=120,
                        y=135,
                        text="3x+6=15",
                    ),
                ),
            ],
            check_question="Какой множитель мы применили к числу 2?",
            final_result="needs_reexplanation",
            final_summary="Student made a distribution mistake and needs a smaller hint.",
        )

    def _build_check_step(
        self,
        *,
        turn_id: str,
        payload: CheckStepPayload,
        judge: JudgeResponse,
    ) -> TutoringStep:
        step_suffix = turn_id.replace("turn_", "")
        bounds = payload.active_region_bounds
        feedback_text = judge.next_hint
        if judge.is_correct is True:
            feedback_text = "Отлично, шаг верный."

        board_actions: list[PlannedBoardAction] = [
            PlannedBoardAction(
                action_id=f"chk_focus_{step_suffix}",
                schedule=ScheduleAtStart(),
                action=FocusRegionAction(
                    region_id=f"student_region_{step_suffix}",
                    bounds=bounds,
                ),
            ),
            PlannedBoardAction(
                action_id=f"chk_highlight_{step_suffix}",
                schedule=ScheduleAnchor(anchor_id="a1", offset_ms=40),
                action=HighlightRegionAction(
                    region_id=f"student_region_{step_suffix}",
                    bounds=bounds,
                    label="Текущий шаг",
                ),
            ),
        ]

        if judge.is_correct is not True:
            board_actions.append(
                PlannedBoardAction(
                    action_id=f"chk_pulse_{step_suffix}",
                    schedule=ScheduleAnchor(anchor_id="a2", offset_ms=0),
                    action=PulseRegionAction(
                        region_id=f"student_region_{step_suffix}",
                        bounds=bounds,
                    ),
                )
            )

        board_actions.append(
            PlannedBoardAction(
                action_id=f"chk_feedback_{step_suffix}",
                schedule=ScheduleAnchor(anchor_id="a3", offset_ms=40),
                action=CreateTextAction(
                    shape_id=f"check_feedback_{step_suffix}",
                    x=bounds.x,
                    y=bounds.y + bounds.h + 22,
                    text=feedback_text,
                ),
            )
        )

        is_correct = judge.is_correct is True
        narration = _build_check_narration(judge, expected_step=payload.expected_step)
        check_question = (
            "Почему здесь получается +6 после раскрытия скобок?"
            if is_correct
            else "Какое число должно получиться при умножении 3 на 2?"
        )
        return TutoringStep(
            step_id="check_step_1",
            narration=narration,
            anchor_names=["focus_region", "highlight_step", "write_feedback"],
            board_actions=board_actions,
            check_question=check_question,
            final_result="ok" if is_correct else "needs_reexplanation",
            final_summary=judge.next_hint,
        )


def _build_check_narration(judge: JudgeResponse, *, expected_step: str) -> str:
    if judge.is_correct is True:
        return (
            "Отличная работа, этот шаг верный. "
            "Сравни со строкой ожидания и убедись, что переход выполнен аккуратно."  # noqa: RUF001
        )

    if judge.is_correct is False:
        return (
            "В этом шаге есть небольшая неточность. "  # noqa: RUF001
            f"{judge.next_hint} Эталонный шаг выглядит так: {expected_step}."
        )

    return (
        "Пока не могу уверенно подтвердить шаг. "
        f"{judge.next_hint} Ожидаемый вид шага: {expected_step}."
    )


def _chunk_audio_bytes(audio: bytes, *, chunk_size: int) -> list[tuple[int, bytes]]:
    if not audio:
        return []

    chunks: list[tuple[int, bytes]] = []
    for seq, start in enumerate(range(0, len(audio), chunk_size)):
        chunks.append((seq, audio[start : start + chunk_size]))
    return chunks


def _resolve_anchor_timings(
    *,
    step: TutoringStep,
    fallback_duration_ms: int,
    explicit_audio_anchor_ms: int | None,
    provider_anchors: list[AnchorTiming],
) -> list[AnchorTiming]:
    if provider_anchors:
        return list(provider_anchors)

    if not step.anchor_names:
        return []

    if explicit_audio_anchor_ms is not None and explicit_audio_anchor_ms > 0:
        spacing = max(300, explicit_audio_anchor_ms // max(len(step.anchor_names), 1))
    else:
        spacing = max(350, fallback_duration_ms // max(len(step.anchor_names), 1))

    return [
        AnchorTiming(anchor_id=f"a{idx + 1}", name=name, time_ms=idx * spacing)
        for idx, name in enumerate(step.anchor_names)
    ]


def _resolve_duration_ms(audio: AudioTransportState, anchors: list[AnchorTiming], narration: str) -> int:
    if audio.has_audio:
        return max(audio.duration_ms, 800)

    if anchors:
        last_anchor_ms = anchors[-1].time_ms
        return max(last_anchor_ms + 500, 1500)

    return max(len(narration) * 30, 1500)
