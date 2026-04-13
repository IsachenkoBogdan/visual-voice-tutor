from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from visual_voice_tutor.config.settings import Settings
from visual_voice_tutor.contracts.context_model import TutorContextModel
from visual_voice_tutor.contracts.judge import JudgeResponse


@dataclass(slots=True)
class JudgeMeta:
    source: str


class HybridJudgeService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def evaluate(self, context: TutorContextModel) -> tuple[JudgeResponse, JudgeMeta]:
        deterministic = _deterministic_step_check(context)
        if deterministic is not None:
            return deterministic, JudgeMeta(source="deterministic")

        model_based = await self._model_based_check(context)
        if model_based is not None:
            return model_based, JudgeMeta(source="azure_openai")

        fallback = JudgeResponse(
            recognized_content=context.student_attempt.recognized_text or "",
            is_legible=context.student_attempt.is_legible,
            is_correct=None,
            confidence=0.4,
            error_type="insufficient_context",
            teacher_response_mode="ask_for_clarification",
            next_hint="Я пока не уверен в этом шаге. Напиши строку ещё раз крупнее.",
        )
        return fallback, JudgeMeta(source="fallback")

    async def _model_based_check(self, context: TutorContextModel) -> JudgeResponse | None:
        if not (
            self._settings.azure_openai_endpoint
            and self._settings.azure_openai_api_key
            and self._settings.azure_openai_deployment
        ):
            return None

        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        url = (
            f"{endpoint}/openai/deployments/{self._settings.azure_openai_deployment}"
            "/chat/completions?api-version=2024-10-21"
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "Ты математический ассистент для 4-7 класса. "
                    "Верни только JSON для JudgeResponse без пояснений."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context.model_dump(mode="json"), ensure_ascii=False),
            },
        ]

        request_body = {
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "api-key": self._settings.azure_openai_api_key,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(url, headers=headers, json=request_body)
                response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return JudgeResponse.model_validate(parsed)
        except Exception:
            return None


def _deterministic_step_check(context: TutorContextModel) -> JudgeResponse | None:
    recognized = (context.student_attempt.recognized_text or "").strip()
    expected = context.teaching_state.expected_step.strip()

    if not recognized:
        return JudgeResponse(
            recognized_content="",
            is_legible=False,
            is_correct=None,
            confidence=0.3,
            error_type="empty_attempt",
            teacher_response_mode="ask_for_clarification",
            next_hint="Я пока не вижу твоего шага. Напиши следующую строку на доске.",
        )

    normalized_recognized = _normalize_math_text(recognized)
    normalized_expected = _normalize_math_text(expected)

    if normalized_recognized == normalized_expected:
        return JudgeResponse(
            recognized_content=recognized,
            is_legible=True,
            is_correct=True,
            confidence=0.95,
            error_type=None,
            teacher_response_mode="give_small_hint",
            next_hint="Отлично, шаг верный. Готов перейти к следующему шагу?",
        )

    # Deterministic check for common distribution mistake in 3(x+2)=15.
    if "3x+8=15" in normalized_recognized and "3x+6=15" in normalized_expected:
        return JudgeResponse(
            recognized_content=recognized,
            is_legible=True,
            is_correct=False,
            confidence=0.9,
            error_type="distribution_error",
            teacher_response_mode="give_small_hint",
            next_hint="Проверь произведение 3*2 внутри скобок.",
        )

    if _seems_equation(normalized_recognized) and _seems_equation(normalized_expected):
        return JudgeResponse(
            recognized_content=recognized,
            is_legible=True,
            is_correct=False,
            confidence=0.78,
            error_type="step_mismatch",
            teacher_response_mode="give_small_hint",
            next_hint="Сравни левую часть после раскрытия скобок и предыдущую строку.",
        )

    return None


def _normalize_math_text(value: str) -> str:
    normalized = value.lower().replace(" ", "")
    normalized = normalized.replace("\u00d7", "*").replace("\u0445", "x")
    return normalized


def _seems_equation(value: str) -> bool:
    return "=" in value and any(ch.isdigit() for ch in value)
