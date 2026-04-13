import {
  BoardShapeSnapshot,
  Bounds,
  CheckStepPayload,
  PlannedBoardAction,
  WhiteboardAction,
} from "@/lib/contracts";
import { Editor, TLShape, TLShapeId, createShapeId, toRichText } from "tldraw";

function toShapeId(rawId: string): TLShapeId {
  return (rawId.startsWith("shape:") ? rawId : createShapeId(rawId)) as TLShapeId;
}

function createText(editor: Editor, action: Extract<WhiteboardAction, { type: "create_text" }>): void {
  editor.createShape({
    id: toShapeId(action.shape_id),
    type: "text",
    x: action.x,
    y: action.y,
    props: {
      color: "black",
      size: "m",
      font: "draw",
      textAlign: "start",
      w: Math.max(100, action.text.length * 8),
      richText: toRichText(action.text),
      scale: 1,
      autoSize: true,
    },
  });
}

function createShape(editor: Editor, action: Extract<WhiteboardAction, { type: "create_shape" }>): void {
  editor.createShape({
    id: toShapeId(action.shape_id),
    type: "geo",
    x: action.x,
    y: action.y,
    props: {
      geo: action.shape === "ellipse" ? "ellipse" : "rectangle",
      dash: "solid",
      url: "",
      w: action.w,
      h: action.h,
      growY: 0,
      scale: 1,
      labelColor: "black",
      color: "blue",
      fill: "none",
      size: "m",
      font: "draw",
      align: "middle",
      verticalAlign: "middle",
      richText: toRichText(action.label ?? ""),
    },
  });
}

function updateText(editor: Editor, action: Extract<WhiteboardAction, { type: "update_text" }>): void {
  const shapeId = toShapeId(action.shape_id);
  const shape = editor.getShape(shapeId);
  if (!shape) {
    return;
  }

  if (shape.type === "text") {
    editor.updateShape({
      id: shape.id,
      type: "text",
      props: {
        richText: toRichText(action.text),
      },
    });
    return;
  }

  if (shape.type === "geo") {
    editor.updateShape({
      id: shape.id,
      type: "geo",
      props: {
        richText: toRichText(action.text),
      },
    });
  }
}

function highlightRegion(
  editor: Editor,
  action: Extract<WhiteboardAction, { type: "highlight_region" | "pulse_region" }>,
): void {
  const shapeId =
    action.type === "highlight_region"
      ? toShapeId(`highlight_${action.region_id}`)
      : toShapeId(`pulse_${action.region_id}`);

  editor.createShape({
    id: shapeId,
    type: "geo",
    x: action.bounds.x,
    y: action.bounds.y,
    props: {
      geo: "rectangle",
      dash: action.type === "highlight_region" ? "solid" : "dashed",
      url: "",
      w: action.bounds.w,
      h: action.bounds.h,
      growY: 0,
      scale: 1,
      labelColor: "black",
      color: "yellow",
      fill: "none",
      size: "m",
      font: "draw",
      align: "middle",
      verticalAlign: "middle",
      richText: toRichText(action.type === "highlight_region" ? (action.label ?? "") : ""),
    },
  });
}

function focusRegion(editor: Editor, action: Extract<WhiteboardAction, { type: "focus_region" }>): void {
  editor.zoomToBounds(
    {
      x: action.bounds.x,
      y: action.bounds.y,
      w: action.bounds.w,
      h: action.bounds.h,
    },
    {
      animation: { duration: 280 },
      targetZoom: 1,
    },
  );
}

function drawArrow(editor: Editor, action: Extract<WhiteboardAction, { type: "draw_arrow" }>): void {
  editor.createShape({
    id: toShapeId(action.shape_id),
    type: "arrow",
    x: 0,
    y: 0,
    props: {
      kind: "arc",
      labelColor: "black",
      color: "blue",
      fill: "none",
      dash: "solid",
      size: "m",
      arrowheadStart: "none",
      arrowheadEnd: "arrow",
      font: "draw",
      start: { x: action.from_x, y: action.from_y },
      end: { x: action.to_x, y: action.to_y },
      bend: 0,
      richText: toRichText(action.label ?? ""),
      labelPosition: 0.5,
      scale: 1,
      elbowMidPoint: 0.5,
    },
  });
}

export function applyBoardAction(editor: Editor, planned: PlannedBoardAction): void {
  const action = planned.action;

  switch (action.type) {
    case "create_text":
      createText(editor, action);
      return;
    case "create_shape":
      createShape(editor, action);
      return;
    case "update_text":
      updateText(editor, action);
      return;
    case "delete_shape":
      editor.deleteShape(toShapeId(action.shape_id));
      return;
    case "highlight_region":
      highlightRegion(editor, action);
      return;
    case "focus_region":
      focusRegion(editor, action);
      return;
    case "draw_arrow":
      drawArrow(editor, action);
      return;
    case "pulse_region":
      highlightRegion(editor, action);
      return;
    case "reveal_group":
      return;
    default:
      return;
  }
}

interface CheckStepDraft {
  problemText: string;
  expectedStep: string;
  recognizedText?: string;
}

export function buildCheckStepPayload(editor: Editor, draft: CheckStepDraft): CheckStepPayload {
  const relevantShapes = extractRelevantShapes(editor);
  return {
    problem_text: draft.problemText,
    expected_step: draft.expectedStep,
    recognized_text: draft.recognizedText?.trim() || null,
    active_region_bounds: resolveActiveRegion(editor, relevantShapes),
    relevant_shapes: relevantShapes,
  };
}

function extractRelevantShapes(editor: Editor): BoardShapeSnapshot[] {
  const pageShapes = editor.getCurrentPageShapes();
  const selected = editor.getSelectedShapeIds();

  const ids =
    selected.length > 0
      ? selected
      : pageShapes
          .slice(Math.max(0, pageShapes.length - 24))
          .map((shape) => shape.id);

  const shapeById = new Map(pageShapes.map((shape) => [shape.id, shape] as const));
  const snapshots: BoardShapeSnapshot[] = [];

  for (const shapeId of ids) {
    const shape = shapeById.get(shapeId);
    const bounds = editor.getShapePageBounds(shapeId);
    if (!shape || !bounds) {
      continue;
    }

    snapshots.push({
      id: shape.id,
      type: shape.type,
      x: bounds.x,
      y: bounds.y,
      w: bounds.w,
      h: bounds.h,
      text: extractShapeText(shape),
      author: "student",
      semantic_tag: inferSemanticTag(shape),
    });
  }

  return snapshots;
}

function resolveActiveRegion(editor: Editor, shapes: BoardShapeSnapshot[]): Bounds {
  if (shapes.length > 0) {
    const first = shapes[0];
    let minX = first.x;
    let minY = first.y;
    let maxX = first.x + first.w;
    let maxY = first.y + first.h;

    for (const shape of shapes.slice(1)) {
      minX = Math.min(minX, shape.x);
      minY = Math.min(minY, shape.y);
      maxX = Math.max(maxX, shape.x + shape.w);
      maxY = Math.max(maxY, shape.y + shape.h);
    }

    return {
      x: minX,
      y: minY,
      w: Math.max(40, maxX - minX),
      h: Math.max(30, maxY - minY),
    };
  }

  const viewport = editor.getViewportPageBounds();
  return {
    x: viewport.x,
    y: viewport.y,
    w: viewport.w,
    h: viewport.h,
  };
}

function extractShapeText(shape: TLShape): string | null {
  const props = shape.props as Record<string, unknown> | undefined;
  if (!props) {
    return null;
  }

  if (typeof props.text === "string" && props.text.trim().length > 0) {
    return props.text.trim();
  }

  return null;
}

function inferSemanticTag(shape: TLShape): string {
  switch (shape.type) {
    case "text":
      return "student_text";
    case "draw":
      return "student_freehand";
    case "geo":
      return "student_shape";
    case "arrow":
      return "student_arrow";
    default:
      return "student_element";
  }
}
