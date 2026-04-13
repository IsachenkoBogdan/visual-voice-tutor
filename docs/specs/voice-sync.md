# Voice Sync Spec

## Goal

Synchronize spoken tutoring narration with whiteboard actions so the tutor feels live and coherent.

---

## Guiding principle

Do not synchronize board actions to raw LLM tokens.
Synchronize to a structured step timeline with semantic anchors.

Each tutoring step consists of:
- narration text
- semantic anchors
- whiteboard actions
- optional micro-sync hints

---

## v0.3 transport model

Voice output uses Azure TTS and is delivered as chunked WebSocket events:

1. `utterance.start`
2. `utterance.ready` (duration + anchors + audio format)
3. `utterance.audio.chunk*`
4. `utterance.audio.end`

When Azure TTS is unavailable, backend falls back to `text+board` mode:
- `utterance.ready.has_audio=false`
- `status` + `error` describing degradation
- board actions still execute

## v0.5 check-step mode

For board-aware checking turns:

1. frontend packages active region + relevant shapes (`check_step`)
2. backend runs hybrid checker (deterministic first, model fallback)
3. backend emits narration + anchors + typed board feedback actions
4. scheduler still binds timeline zero to real playback start

---

## Scheduler anchor point

Playback timeline zero is defined as **actual audio playback start** in frontend runtime.

This means:
- board actions are queued after `utterance.ready`
- timers are armed only after `onPlaybackStarted`
- anchor offsets are resolved relative to real playback start

---

## Sync levels

### Level 1 — semantic sync (primary)

Use semantic anchors for:
- show_equation
- highlight_brackets
- write_next_line
- ask_check_question

### Level 2 — micro sync (secondary)

Use only for subtle emphasis and visual pulses.

---

## Cancellation model

If student interrupts:

1. stop audio playback
2. clear pending chunk buffers
3. cancel future anchor callbacks
4. cancel not-yet-applied board actions
5. keep turn marked incomplete

Never continue applying actions from an interrupted turn.

---

## Production rules

- keep narration chunks short
- prefer 1–3 visual actions per chunk
- prefer semantic sync over hyper-granular token sync
- avoid long action queues
- always support interruption-safe rollback
