# Context Model Spec

## Goal

Provide the model with enough context to:
- understand the student’s current work
- judge whether the step is correct
- decide what to say next
- decide what to draw next

without overloading the model with the entire whiteboard state on every turn.

---

## Principle

Use hybrid context:
- visual context
- structured board context
- recent action context
- teaching state
- explicit evaluation target

Never send only a screenshot.
Never send only raw board JSON.

---

## Main context object

```json
{
  "problem": {
    "original_text": "Реши уравнение 3(x+2)=15",
    "topic": "linear_equation",
    "grade_band": "4-7"
  },
  "teaching_state": {
    "current_goal": "check student expansion step",
    "expected_step": "3x+6=15",
    "teaching_mode": "guided_check",
    "last_system_summary": "The tutor asked the student to expand the brackets."
  },
  "board_context": {
    "full_board_thumbnail_url": "https://example.com/full_board.png",
    "active_crop_url": "https://example.com/active_crop.png",
    "selected_shape_ids": ["s1", "s2"],
    "relevant_shapes": [],
    "recent_actions": []
  },
  "student_attempt": {
    "active_region_bounds": { "x": 120, "y": 80, "w": 280, "h": 140 },
    "recognized_text": "3x+8=15",
    "is_legible": true,
    "confidence": 0.84
  },
  "learner_memory": {
    "recurring_mistakes": ["sign_errors", "distribution_errors"],
    "pace_preference": "slow",
    "recent_outcomes": ["needed_reexplanation"]
  },
  "task": {
    "type": "judge_student_step",
    "instruction": "Determine whether the student expanded the brackets correctly. If wrong, return the smallest helpful next hint."
  }
}
````

---

## Relevant shapes format

Each relevant shape should include:

* id
* type
* author: student | tutor | system
* text if applicable
* bounds
* parent/group id
* z-order
* semantic tag if available

Freehand shapes should include:

* stroke points
* bounds
* created_at
* grouped cluster id

Example:

```json
{
  "id": "shape_12",
  "type": "text",
  "author": "student",
  "text": "3x+8=15",
  "bounds": { "x": 140, "y": 120, "w": 120, "h": 24 },
  "parent_group_id": "attempt_group_1",
  "z_index": 18,
  "semantic_tag": "student_current_line"
}
```

Freehand example:

```json
{
  "id": "stroke_22",
  "type": "freehand",
  "author": "student",
  "points": [[10, 12], [11, 13], [14, 18]],
  "bounds": { "x": 180, "y": 160, "w": 42, "h": 19 },
  "created_at": "2026-04-14T12:34:56Z",
  "cluster_id": "cluster_4"
}
```

---

## Recent actions

Only include the most recent meaningful actions:

* create stroke
* create text
* erase region
* move shape
* edit text

This helps the model see the student’s thought process.

Example:

```json
[
  {
    "type": "create_text",
    "shape_id": "shape_12",
    "author": "student",
    "timestamp": "2026-04-14T12:34:56Z"
  },
  {
    "type": "edit_text",
    "shape_id": "shape_12",
    "author": "student",
    "timestamp": "2026-04-14T12:34:58Z"
  }
]
```

---

## Student attempt package

The student attempt should isolate the current work to check.

It should contain:

* active bounds
* recognized text if any
* image crop
* relevant shapes
* recognition confidence
* ambiguity flag

Example:

```json
{
  "active_region_bounds": { "x": 120, "y": 80, "w": 280, "h": 140 },
  "crop_url": "https://example.com/attempt_crop.png",
  "recognized_text": "3x+8=15",
  "relevant_shape_ids": ["shape_12", "stroke_22"],
  "confidence": 0.84,
  "ambiguity_flag": false
}
```

---

## Model task types

Allowed task types:

* judge_student_step
* interpret_student_drawing
* decide_next_hint
* summarize_confusion
* classify_error_type

Every request must include exactly one explicit task type.

---

## Judge response format

```json
{
  "recognized_content": "3x+8=15",
  "is_legible": true,
  "is_correct": false,
  "confidence": 0.88,
  "error_type": "distribution_error",
  "teacher_response_mode": "give_small_hint",
  "next_hint": "Проверь, на что умножается число 2 внутри скобок."
}
```

If confidence is low:

```json
{
  "recognized_content": "possibly 3x+6=15",
  "is_legible": false,
  "is_correct": null,
  "confidence": 0.39,
  "error_type": "ambiguous_handwriting",
  "teacher_response_mode": "ask_for_clarification",
  "next_hint": "Я не до конца разобрал последнюю строку. Обведи её или напиши крупнее."
}
```

---

## Storage split

### Hot context

Kept in Redis:

* current active region
* recent board actions
* active turn
* pending checks

### Persistent context

Kept in Postgres:

* learner memory
* session summaries
* recurring patterns

### Artifact context

Kept in Storage:

* thumbnails
* crops
* audio
* replay assets