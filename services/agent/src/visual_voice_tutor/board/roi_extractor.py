from __future__ import annotations

from visual_voice_tutor.contracts.whiteboard import Bounds


def extract_active_region(raw_bounds: dict[str, float] | None = None) -> Bounds:
    """Return a safe active region for model checking and hint generation."""

    if raw_bounds is None:
        return Bounds(x=100, y=70, w=360, h=180)

    return Bounds(
        x=float(raw_bounds.get("x", 100.0)),
        y=float(raw_bounds.get("y", 70.0)),
        w=float(raw_bounds.get("w", 360.0)),
        h=float(raw_bounds.get("h", 180.0)),
    )
