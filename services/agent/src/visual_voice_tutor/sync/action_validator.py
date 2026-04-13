from __future__ import annotations

from pydantic import ValidationError

from visual_voice_tutor.contracts.whiteboard import PlannedBoardAction


class ActionValidationError(ValueError):
    pass


def validate_actions(actions: list[PlannedBoardAction]) -> list[PlannedBoardAction]:
    """Validate board actions through pydantic model round-trip."""

    validated: list[PlannedBoardAction] = []
    for action in actions:
        try:
            validated.append(PlannedBoardAction.model_validate(action.model_dump(mode="python")))
        except ValidationError as exc:  # pragma: no cover - defensive guard
            raise ActionValidationError(str(exc)) from exc

    return validated
