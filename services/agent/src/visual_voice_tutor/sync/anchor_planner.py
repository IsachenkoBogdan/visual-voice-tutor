from __future__ import annotations

from visual_voice_tutor.contracts.stream_events import AnchorTiming


def build_anchor_time_index(anchors: list[AnchorTiming]) -> dict[str, int]:
    """Map anchor ids to offsets in milliseconds."""

    return {anchor.anchor_id: anchor.time_ms for anchor in anchors}
