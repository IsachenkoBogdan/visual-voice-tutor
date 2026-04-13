# Visual Voice Tutor

Production-minded monorepo для realtime мультимодального math tutor (4–7 класс).

## Текущее состояние

- Next.js tutor shell с `tldraw`, websocket runtime, scheduler и ASR/TTS streaming hooks
- FastAPI orchestrator с typed contracts, board-aware checking, mock + real Azure hooks
- Learner/session/billing groundwork:
  - learner profiles
  - session history
  - usage accounting
  - entitlement checks
- Observability groundwork:
  - Langfuse event hooks
  - runtime metrics snapshot API
- CI в `.github/workflows/ci.yml`

## Быстрый старт

```bash
uv sync
uv run vvt-api
```

В отдельном терминале:

```bash
cd apps/web
npm ci
npm run dev
```

## Основные URL

- Web home: `http://localhost:3000/`
- Tutor runtime: `http://localhost:3000/tutor`
- Learners shell: `http://localhost:3000/learners`
- Billing shell: `http://localhost:3000/billing`
- Backend health: `http://localhost:8000/health`

## API surface (v1 groundwork)

- `GET /api/v1/accounts/{user_id}`
- `GET /api/v1/accounts/{user_id}/learners`
- `GET /api/v1/learners/{learner_id}`
- `GET /api/v1/learners/{learner_id}/sessions`
- `GET /api/v1/billing/plans`
- `GET /api/v1/billing/subscription/{learner_id}`
- `GET /api/v1/billing/entitlement/{learner_id}`
- `GET /api/v1/ops/metrics`

## Auth gate (optional)

Если включить:

```env
API_AUTH_ENABLED=true
API_AUTH_TOKEN=super-secret
NEXT_PUBLIC_API_KEY=super-secret
```

то HTTP API и WS runtime требуют токен (`x-api-key`, `Authorization: Bearer ...` или `api_key` query).
