from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class Bounds(BaseModel):
    x: float
    y: float
    w: float
    h: float


class ScheduleAtStart(BaseModel):
    mode: Literal["at_start"] = "at_start"


class ScheduleAtEnd(BaseModel):
    mode: Literal["at_end"] = "at_end"


class ScheduleAnchor(BaseModel):
    mode: Literal["anchor"] = "anchor"
    anchor_id: str
    offset_ms: int = 0


BoardActionSchedule = Annotated[
    ScheduleAtStart | ScheduleAtEnd | ScheduleAnchor,
    Field(discriminator="mode"),
]


class CreateTextAction(BaseModel):
    type: Literal["create_text"] = "create_text"
    shape_id: str
    x: float
    y: float
    text: str


class CreateShapeAction(BaseModel):
    type: Literal["create_shape"] = "create_shape"
    shape_id: str
    x: float
    y: float
    w: float
    h: float
    shape: Literal["rectangle", "ellipse"] = "rectangle"
    label: str | None = None


class UpdateTextAction(BaseModel):
    type: Literal["update_text"] = "update_text"
    shape_id: str
    text: str


class DeleteShapeAction(BaseModel):
    type: Literal["delete_shape"] = "delete_shape"
    shape_id: str


class HighlightRegionAction(BaseModel):
    type: Literal["highlight_region"] = "highlight_region"
    region_id: str
    bounds: Bounds
    label: str | None = None


class RevealGroupAction(BaseModel):
    type: Literal["reveal_group"] = "reveal_group"
    group_id: str


class FocusRegionAction(BaseModel):
    type: Literal["focus_region"] = "focus_region"
    region_id: str
    bounds: Bounds


class DrawArrowAction(BaseModel):
    type: Literal["draw_arrow"] = "draw_arrow"
    shape_id: str
    from_x: float
    from_y: float
    to_x: float
    to_y: float
    label: str | None = None


class PulseRegionAction(BaseModel):
    type: Literal["pulse_region"] = "pulse_region"
    region_id: str
    bounds: Bounds


WhiteboardAction = Annotated[
    CreateTextAction
    | CreateShapeAction
    | UpdateTextAction
    | DeleteShapeAction
    | HighlightRegionAction
    | RevealGroupAction
    | FocusRegionAction
    | DrawArrowAction
    | PulseRegionAction,
    Field(discriminator="type"),
]


class PlannedBoardAction(BaseModel):
    action_id: str
    schedule: BoardActionSchedule
    action: WhiteboardAction
