# Stream Events Spec

## Goal

The backend sends typed runtime events to the frontend over WebSocket.

The frontend never infers whiteboard actions from plain text narration.
It only executes validated typed actions.

---

## Event envelope

Every event uses this envelope:

```json
{
  "type": "status",
  "request_id": "req_123",
  "session_id": "sess_123",
  "turn_id": "turn_123",
  "timestamp": "2026-04-14T12:34:56Z",
  "payload": {}
}
```

---

## Event types

### `status`

Short lifecycle message.

### `utterance.start`

Marks the start of a narration chunk.

### `utterance.ready`

Timing and audio format metadata are ready.

```json
{
  "type": "utterance.ready",
  "payload": {
    "utterance_id": "utt_1",
    "duration_ms": 2150,
    "anchors": [
      { "anchor_id": "a1", "kind": "bookmark", "name": "show_equation", "time_ms": 0 },
      { "anchor_id": "a2", "kind": "bookmark", "name": "highlight_brackets", "time_ms": 900 }
    ],
    "encoding": "mp3",
    "sample_rate_hz": 24000,
    "channels": 1,
    "has_audio": true,
    "fallback_reason": null
  }
}
```

### `utterance.audio.chunk`

Audio transport chunk over WebSocket.

```json
{
  "type": "utterance.audio.chunk",
  "payload": {
    "utterance_id": "utt_1",
    "seq": 0,
    "chunk_b64": "...",
    "chunk_size_bytes": 16384,
    "encoding": "mp3",
    "sample_rate_hz": 24000,
    "channels": 1
  }
}
```

### `utterance.audio.end`

Marks end of chunked audio stream for one utterance.

```json
{
  "type": "utterance.audio.end",
  "payload": {
    "utterance_id": "utt_1",
    "total_chunks": 6,
    "total_bytes": 98124
  }
}
```

### `board.action`

A single validated whiteboard action.

### `board.batch_done`

Marks completion of a visual step batch.

### `check.question`

Tutor follow-up question for quick understanding check.

### `asr.partial`

Partial ASR hypothesis for incoming student audio chunk.

### `asr.final`

Final ASR transcription for incoming student audio chunk.

### `final`

Final result of the turn.

### `error`

Recoverable or terminal error.

### `interrupt`

Signals that current turn was interrupted and future actions must be cancelled.

---

## Runtime commands (frontend -> backend)

### `run_mock_turn`

Starts one mocked tutoring turn.

### `check_step`

Starts board-aware checking turn with typed payload:

```json
{
  "type": "check_step",
  "payload": {
    "problem_text": "Реши уравнение 3(x+2)=15",
    "expected_step": "3x+6=15",
    "recognized_text": "3x+8=15",
    "active_region_bounds": { "x": 120, "y": 80, "w": 280, "h": 140 },
    "relevant_shapes": [
      {
        "id": "shape_12",
        "type": "text",
        "x": 140,
        "y": 120,
        "w": 120,
        "h": 24,
        "text": "3x+8=15",
        "author": "student",
        "semantic_tag": "student_current_line"
      }
    ]
  }
}
```

### `asr.transcribe`

Submits one base64 audio payload for ASR:

```json
{
  "type": "asr.transcribe",
  "payload": {
    "audio_b64": "...",
    "mime_type": "audio/wav"
  }
}
```

### `interrupt`

Stops active turn and cancels not-yet-applied actions.

---

## Audio transport rules

- Audio transport is `chunked WebSocket`.
- Chunks are ordered by `seq` per `utterance_id`.
- Frontend must handle duplicate chunks idempotently by key `(utterance_id, seq)`.
- `utterance.audio.end` finalizes the chunk stream for playback assembly.

---

## Scheduling model

Each `board.action` must target one of:

- `at_start`
- `anchor_id`
- `after_anchor_ms`
- `at_end`

The frontend scheduler resolves these against playback timeline.
Timeline zero must be bound to the actual audio playback start.

---

## Cancellation rules

If `interrupt` is received:

- stop audio playback
- clear audio chunk buffers
- cancel all not-yet-applied actions
- do not apply future actions from interrupted turn
- mark turn incomplete
