# System Design

# Visual Voice Tutor

## 1. Goal

Build a production-oriented multimodal tutoring system that:
- hears the student
- understands the student’s current attempt
- explains the next step in Russian
- updates the whiteboard in sync with speech
- checks whether the student understood
- stores long-term learner memory
- evolves version by version into a paid product

---

## 2. Chosen architecture

## Frontend
- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- tldraw
- client-side playback scheduler
- websocket client

## Backend
- Python FastAPI service
- WebSocket stream endpoint
- custom tutoring orchestrator
- board context builder
- correctness checking
- memory management
- evaluation layer

## External services
- Azure Speech for ASR and TTS
- Azure OpenAI / Foundry for model inference
- Supabase for persistent storage
- Redis for hot session state
- Langfuse for LLM observability
- Grafana stack for infra observability

---

## 3. Versioning strategy

The product will be developed in staged versions.

Version roadmap is defined in `VERSIONS.md`.

Principles:
- keep frontend and infra quality high from the start
- keep runtime path simple
- add product features gradually
- do not ship broad scope before the tutoring core is reliable

---

## 4. Main runtime flow

1. The student speaks, types, or draws on the whiteboard.
2. The frontend sends:
   - transcript or input
   - board delta
   - active region metadata
3. The backend updates live session state.
4. The backend builds a tutoring context package.
5. The orchestrator decides the next pedagogical step.
6. The backend produces:
   - narration text
   - semantic anchors
   - whiteboard actions
7. Azure TTS synthesizes the narration.
8. The backend streams typed events to the frontend.
9. The frontend playback scheduler:
   - starts audio
   - schedules whiteboard actions
   - handles interruption and rollback
10. The student reacts.
11. The backend checks the student response.
12. The backend updates session summary and learner memory.

---

## 5. Main modules

### 5.1 Orchestrator
Responsible for:
- step planning
- selecting the next teaching action
- choosing explain / ask / check / repair
- deciding when to update memory

### 5.2 Board Context Builder
Responsible for:
- full-board thumbnail
- active crop
- structured board JSON
- recent student actions
- student-attempt packaging

### 5.3 Correctness Layer
Responsible for:
- deterministic checks where possible
- model-based checking where needed
- ambiguity handling
- confidence scoring

### 5.4 Voice Layer
Responsible for:
- Azure ASR
- Azure TTS
- timing-aware speech output
- interruption hooks

### 5.5 Playback Scheduler
Responsible for:
- narration timeline execution
- semantic anchor execution
- whiteboard action timing
- cancellation of future actions

### 5.6 Memory Layer
Responsible for:
- Redis live state
- Postgres learner memory
- storage artifacts
- session summaries

### 5.7 Evaluation Layer
Responsible for:
- tutor review
- automated evaluation
- version comparison

### 5.8 Billing Layer
Not active in early versions.
Later responsible for:
- product plans
- subscription state
- entitlements
- usage accounting

---

## 6. Synchronization strategy

Synchronization is timeline-based.

The backend does not stream arbitrary narration and expect the frontend to infer drawing behavior.

Instead, the backend produces a structured step:
- narration
- semantic anchors
- board action batches
- optional micro-sync hints

The frontend uses this structure plus Azure timing data to apply actions at the right moments.

### Primary sync mechanism
Semantic anchors:
- show_equation
- focus_region
- highlight_brackets
- write_next_line
- ask_check_question

### Secondary sync mechanism
Word-level timing for:
- small highlight effects
- token emphasis
- subtle cues

The product should rely mostly on semantic sync.

---

## 7. Context strategy for model input

The model receives hybrid context:

### Visual context
- full board thumbnail
- active crop

### Structured context
- typed shapes
- grouped strokes
- bounds and positions
- recent edits
- authorship metadata

### Teaching context
- original problem
- current expected step
- last explanation summary
- explicit evaluation target

The model must always receive a narrow task.
Do not ask only “is this correct?” without specifying what to evaluate.

---

## 8. State and memory

### Live session state in Redis
- active turn id
- pending narration
- pending anchors
- pending board actions
- interruption flags
- replay buffer
- current teaching mode

### Persistent state in Supabase
- users
- learners
- sessions
- session summaries
- recurring mistakes
- weak topics
- tutor evaluations
- automated evaluations
- later billing state

### Artifacts in Storage
- audio
- board exports
- screenshots
- replay assets

---

## 9. Observability

### Instrumentation
Use OpenTelemetry across backend runtime.

### LLM/product observability
Use Langfuse for:
- traces
- prompt versions
- cost
- latency
- eval datasets
- experiments

### Infra observability
Use Grafana stack for:
- logs
- traces
- dashboards
- alerts

Track:
- time to first response
- ASR latency
- TTS latency
- sync drift
- interruption rate
- action validation failures
- Redis failures
- storage failures

---

## 10. Framework decisions

### tldraw
Use as the whiteboard and visual interaction layer.

### LangGraph
Do not use in the live tutoring path.
May be introduced later for slow-path workflows.

### Mem0
Do not use as source of truth in v1.
May be evaluated later as optional memory enrichment.

---

## 11. Failure modes and fallback

### TTS timing degraded
Fallback:
- semantic anchors only
- disable fine-grained micro-sync

### ASR low confidence
Fallback:
- ask the student to repeat
- offer text input
- ask the student to mark the region on the board

### Board interpretation ambiguous
Fallback:
- ask the student to circle the line to check
- ask the student to rewrite larger

### Model uncertainty
Fallback:
- do not confidently judge correctness
- switch to clarification mode

### Interruption
Fallback:
- stop audio
- cancel not-yet-applied actions
- cut current turn
- resume planning from the partial state

---

## 12. Operational constraints

### Latency
- ideal time to first response: < 1 second
- acceptable p95 for early production: < 5 seconds

### Solo-builder constraint
- architecture must remain understandable and operable by one person

### Product constraint
- one excellent tutoring loop is more valuable than broad unfinished scope

## Frontend design role

The frontend is the product shell and real-time interaction layer.

It is responsible for:
- rendering the tutor interface
- hosting the whiteboard
- playing audio
- applying timed whiteboard actions
- handling websocket events
- exposing future product surfaces such as settings, learner pages, and billing pages

It is not responsible for:
- tutoring orchestration
- long-term memory decisions
- correctness checking
- model routing