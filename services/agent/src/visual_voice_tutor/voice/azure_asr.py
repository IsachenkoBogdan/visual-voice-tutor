from __future__ import annotations

import asyncio

from visual_voice_tutor.voice.asr_provider import AsrError, AsrProvider, AsrResult


class AzureAsrProvider(AsrProvider):
    """Production ASR provider for Azure Speech recognize-once path."""

    def __init__(
        self,
        *,
        speech_key: str,
        speech_region: str,
        language: str,
        timeout_sec: int,
    ) -> None:
        self._speech_key = speech_key
        self._speech_region = speech_region
        self._language = language
        self._timeout_sec = timeout_sec

    async def transcribe_chunk(self, audio_bytes: bytes) -> AsrResult:
        if not self._speech_key or not self._speech_region:
            raise AsrError(
                code="azure_asr_not_configured",
                message="Azure Speech ASR credentials are not configured",
                retryable=False,
            )

        if not audio_bytes:
            return AsrResult(text="", confidence=0.0, is_final=True)

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._transcribe_sync, audio_bytes),
                timeout=self._timeout_sec,
            )
        except TimeoutError as exc:
            raise AsrError(
                code="azure_asr_timeout",
                message="Azure ASR request timed out",
                retryable=True,
            ) from exc

    def _transcribe_sync(self, audio_bytes: bytes) -> AsrResult:
        try:
            import azure.cognitiveservices.speech as speechsdk  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise AsrError(
                code="azure_speech_sdk_missing",
                message="azure-cognitiveservices-speech package is not installed",
                retryable=False,
            ) from exc

        speech_config = speechsdk.SpeechConfig(
            subscription=self._speech_key,
            region=self._speech_region,
        )
        speech_config.speech_recognition_language = self._language

        stream = speechsdk.audio.PushAudioInputStream()
        stream.write(audio_bytes)
        stream.close()

        audio_config = speechsdk.audio.AudioConfig(stream=stream)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        result = recognizer.recognize_once_async().get()

        reason = getattr(result, "reason", None)
        recognized_reason = getattr(speechsdk.ResultReason, "RecognizedSpeech", None)
        if reason != recognized_reason:
            details = getattr(result, "no_match_details", None)
            message = str(details) if details else "Azure ASR did not recognize speech"
            raise AsrError(
                code="azure_asr_no_match",
                message=message,
                retryable=True,
            )

        text = str(getattr(result, "text", "")).strip()
        if not text:
            raise AsrError(
                code="azure_asr_empty_text",
                message="Azure ASR returned empty text",
                retryable=True,
            )

        return AsrResult(text=text, confidence=0.75, is_final=True)


class AzureAsrStub(AsrProvider):
    """Stub API-compatible layer for local development."""

    async def transcribe_chunk(self, audio_bytes: bytes) -> AsrResult:
        if not audio_bytes:
            return AsrResult(text="", confidence=0.0, is_final=True)
        return AsrResult(text="mock transcript", confidence=0.75, is_final=True)
