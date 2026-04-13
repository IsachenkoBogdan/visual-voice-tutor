from __future__ import annotations

from visual_voice_tutor.contracts.stream_events import AnchorTiming
from visual_voice_tutor.contracts.whiteboard import PlannedBoardAction, ScheduleAnchor
from visual_voice_tutor.sync.anchor_planner import build_anchor_time_index


def with_resolved_timing(
    actions: list[PlannedBoardAction],
    anchors: list[AnchorTiming],
    duration_ms: int,
) -> list[tuple[PlannedBoardAction, int]]:
    """Resolve action schedule to timeline offsets used by clients for debug/ordering."""

    resolved: list[tuple[PlannedBoardAction, int]] = []
    anchor_index = build_anchor_time_index(anchors)

    for action in actions:
        schedule = action.schedule
        match schedule.mode:
            case "at_start":
                resolved_time = 0
            case "at_end":
                resolved_time = duration_ms
            case "anchor":
                if isinstance(schedule, ScheduleAnchor):
                    resolved_time = anchor_index.get(schedule.anchor_id, 0) + schedule.offset_ms
                else:  # pragma: no cover - narrowed by pydantic discriminator
                    resolved_time = 0
            case _:  # pragma: no cover - exhaustive fallback
                resolved_time = 0

        resolved.append((action, max(resolved_time, 0)))

    resolved.sort(key=lambda item: item[1])
    return resolved
