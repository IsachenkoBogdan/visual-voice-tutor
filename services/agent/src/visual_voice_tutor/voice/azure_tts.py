from __future__ import annotations

import asyncio
from html import escape
from typing import Any

from visual_voice_tutor.contracts.stream_events import AnchorTiming
from visual_voice_tutor.voice.tts_provider import (
    TtsAudioFormat,
    TtsProvider,
    TtsSynthesisError,
    TtsSynthesisResult,
)

_OUTPUT_FORMAT_ALIAS: dict[str, tuple[str, TtsAudioFormat]] = {
    "audio-24khz-48kbitrate-mono-mp3": (
        "Audio24Khz48KBitRateMonoMp3",
        TtsAudioFormat(
            encoding="mp3",
            sample_rate_hz=24_000,
            channels=1,
            mime_type="audio/mpeg",
        ),
    ),
    "audio-16khz-32kbitrate-mono-mp3": (
        "Audio16Khz32KBitRateMonoMp3",
        TtsAudioFormat(
            encoding="mp3",
            sample_rate_hz=16_000,
            channels=1,
            mime_type="audio/mpeg",
        ),
    ),
    "riff-24khz-16bit-mono-pcm": (
        "Riff24Khz16BitMonoPcm",
        TtsAudioFormat(
            encoding="pcm",
            sample_rate_hz=24_000,
            channels=1,
            mime_type="audio/wav",
        ),
    ),
}


class AzureTtsProvider(TtsProvider):
    """Production TTS provider for Azure Speech synthesis."""

    def __init__(
        self,
        *,
        speech_key: str,
        speech_region: str,
        voice_name: str,
        output_format: str,
        request_timeout_sec: int,
    ) -> None:
        self._speech_key = speech_key
        self._speech_region = speech_region
        self._voice_name = voice_name
        self._output_format = output_format
        self._request_timeout_sec = request_timeout_sec

    async def synthesize(
        self, *, utterance_id: str, text: str, anchor_names: list[str]
    ) -> TtsSynthesisResult:
        if not self._speech_key or not self._speech_region:
            raise TtsSynthesisError(
                code="azure_tts_not_configured",
                message="Azure Speech credentials are not configured",
                retryable=False,
            )

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._synthesize_sync,
                    utterance_id,
                    text,
                    anchor_names,
                ),
                timeout=self._request_timeout_sec,
            )
        except TimeoutError as exc:
            raise TtsSynthesisError(
                code="azure_tts_timeout",
                message="Azure TTS request timed out",
                retryable=True,
            ) from exc

    def _synthesize_sync(
        self,
        utterance_id: str,
        text: str,
        anchor_names: list[str],
    ) -> TtsSynthesisResult:
        try:
            import azure.cognitiveservices.speech as speechsdk  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise TtsSynthesisError(
                code="azure_speech_sdk_missing",
                message="azure-cognitiveservices-speech package is not installed",
                retryable=False,
            ) from exc

        output_enum_name, audio_format = _resolve_output_format(self._output_format)
        output_enum = getattr(speechsdk.SpeechSynthesisOutputFormat, output_enum_name, None)
        if output_enum is None:
            raise TtsSynthesisError(
                code="azure_tts_output_format_invalid",
                message=f"Unsupported Azure output format: {self._output_format}",
                retryable=False,
            )

        speech_config = speechsdk.SpeechConfig(
            subscription=self._speech_key,
            region=self._speech_region,
        )
        speech_config.speech_synthesis_voice_name = self._voice_name
        speech_config.set_speech_synthesis_output_format(output_enum)

        bookmark_timings: list[tuple[str, int]] = []

        def on_bookmark(event: Any) -> None:
            # Azure audio_offset is 100-ns units.
            audio_offset_ms = int(getattr(event, "audio_offset", 0) / 10_000)
            bookmark_name = str(getattr(event, "text", ""))
            bookmark_timings.append((bookmark_name, audio_offset_ms))

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None,
        )
        synthesizer.bookmark_reached.connect(on_bookmark)

        result = synthesizer.speak_ssml_async(
            _build_ssml(
                text=text,
                anchor_names=anchor_names,
                voice_name=self._voice_name,
            )
        ).get()

        reason = getattr(result, "reason", None)
        completed = getattr(speechsdk.ResultReason, "SynthesizingAudioCompleted", None)
        if reason != completed:
            details = getattr(result, "error_details", "") or "Unknown Azure TTS failure"
            raise TtsSynthesisError(
                code="azure_tts_failed",
                message=str(details),
                retryable=True,
            )

        audio_bytes = bytes(getattr(result, "audio_data", b""))
        if not audio_bytes:
            raise TtsSynthesisError(
                code="azure_tts_empty_audio",
                message="Azure TTS returned empty audio payload",
                retryable=True,
            )

        anchors = _map_anchor_timings(anchor_names=anchor_names, observed=bookmark_timings, text=text)
        duration_ms = max(
            int((len(audio_bytes) / max(audio_format.sample_rate_hz, 1)) * 1000),
            (anchors[-1].time_ms + 350) if anchors else 500,
        )

        return TtsSynthesisResult(
            utterance_id=utterance_id,
            audio_id=f"audio_{utterance_id}",
            duration_ms=duration_ms,
            anchors=anchors,
            audio_bytes=audio_bytes,
            audio_format=audio_format,
        )


class AzureTtsStub(TtsProvider):
    """Stub API-compatible layer for local runs and tests."""

    def __init__(self, *, output_format: str = "audio-24khz-48kbitrate-mono-mp3") -> None:
        _, audio_format = _resolve_output_format(output_format)
        self._audio_format = audio_format

    async def synthesize(
        self, *, utterance_id: str, text: str, anchor_names: list[str]
    ) -> TtsSynthesisResult:
        anchors: list[AnchorTiming] = []
        step = max(350, int(1800 / max(len(anchor_names), 1)))
        for idx, name in enumerate(anchor_names):
            anchors.append(AnchorTiming(anchor_id=f"a{idx + 1}", name=name, time_ms=idx * step))

        duration_ms = max(2000, len(text) * 32)
        return TtsSynthesisResult(
            utterance_id=utterance_id,
            audio_id=f"audio_{utterance_id}",
            duration_ms=duration_ms,
            anchors=anchors,
            # Stub keeps empty payload to force deterministic fallback in environments without Azure.
            audio_bytes=b"",
            audio_format=self._audio_format,
        )


def _resolve_output_format(output_format: str) -> tuple[str, TtsAudioFormat]:
    key = output_format.strip().lower()
    if key not in _OUTPUT_FORMAT_ALIAS:
        raise TtsSynthesisError(
            code="azure_tts_output_format_invalid",
            message=f"Unsupported Azure output format: {output_format}",
            retryable=False,
        )

    enum_name, fmt = _OUTPUT_FORMAT_ALIAS[key]
    return enum_name, fmt


def _build_ssml(*, text: str, anchor_names: list[str], voice_name: str) -> str:
    escaped_text = escape(text)
    segments = _split_text_for_anchors(escaped_text, max(len(anchor_names), 1))

    body_parts: list[str] = []
    if not anchor_names:
        body_parts.append(escaped_text)
    else:
        for idx, segment in enumerate(segments):
            if idx < len(anchor_names):
                body_parts.append(f'<bookmark mark="{escape(anchor_names[idx])}" />')
            body_parts.append(segment)

    body = " ".join(part for part in body_parts if part)
    return (
        "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"ru-RU\">"
        f"<voice name=\"{escape(voice_name)}\">{body}</voice>"
        "</speak>"
    )


def _split_text_for_anchors(text: str, chunks: int) -> list[str]:
    if chunks <= 1:
        return [text]

    words = text.split()
    if not words:
        return [text]

    bucket_size = max(1, len(words) // chunks)
    grouped: list[str] = []
    for start in range(0, len(words), bucket_size):
        grouped.append(" ".join(words[start : start + bucket_size]))
    return grouped[:chunks] if len(grouped) >= chunks else grouped


def _map_anchor_timings(
    *,
    anchor_names: list[str],
    observed: list[tuple[str, int]],
    text: str,
) -> list[AnchorTiming]:
    if observed:
        lookup = {name: time_ms for name, time_ms in observed}
        anchors: list[AnchorTiming] = []
        fallback_step = max(350, int(max(len(text), 1) * 12 / max(len(anchor_names), 1)))
        for idx, anchor_name in enumerate(anchor_names):
            anchors.append(
                AnchorTiming(
                    anchor_id=f"a{idx + 1}",
                    name=anchor_name,
                    time_ms=lookup.get(anchor_name, idx * fallback_step),
                )
            )
        return anchors

    if not anchor_names:
        return []

    fallback_step = max(350, int(max(len(text), 1) * 12 / len(anchor_names)))
    return [
        AnchorTiming(anchor_id=f"a{idx + 1}", name=name, time_ms=idx * fallback_step)
        for idx, name in enumerate(anchor_names)
    ]
