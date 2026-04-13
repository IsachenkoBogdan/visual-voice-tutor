from __future__ import annotations

from typing import Any

from visual_voice_tutor.contracts.context_model import RelevantShape
from visual_voice_tutor.contracts.whiteboard import Bounds


def map_board_shapes(raw_shapes: list[dict[str, object]]) -> list[RelevantShape]:
    """Map transport-neutral board state into typed relevant shapes."""

    mapped: list[RelevantShape] = []
    for idx, raw in enumerate(raw_shapes):
        bounds_raw = raw.get("bounds")
        if not isinstance(bounds_raw, dict):
            continue

        typed_bounds: dict[str, Any] = {str(key): value for key, value in bounds_raw.items()}
        bounds = _normalize_bounds(typed_bounds)
        mapped.append(
            RelevantShape(
                id=str(raw.get("id", f"shape_{idx}")),
                type=str(raw.get("type", "unknown")),
                author="student",
                text=str(raw.get("text")) if raw.get("text") is not None else None,
                bounds=bounds,
                semantic_tag=str(raw.get("semantic_tag")) if raw.get("semantic_tag") else None,
            )
        )

    return mapped


def _normalize_bounds(raw: dict[str, Any]) -> Bounds:
    return Bounds(
        x=_as_float(raw.get("x"), default=0.0),
        y=_as_float(raw.get("y"), default=0.0),
        w=_as_float(raw.get("w"), default=0.0),
        h=_as_float(raw.get("h"), default=0.0),
    )


def _as_float(value: Any, *, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default
