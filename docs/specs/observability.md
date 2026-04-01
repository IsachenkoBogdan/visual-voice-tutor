# Observability / Evals

## Наблюдаемость

Для первой версии достаточно двух слоев:

- `Langfuse` для LLM/agent traces и eval traces;
- application metrics + structured logs для latency, errors и fallback events.

---

## Ключевые метрики

| Метрика | Описание |
|---|---|
| `request_latency_ms` | end-to-end latency |
| `step_delivery_latency_ms` | latency одного tutoring step |
| `retrieval_latency_ms` | retrieval + reranking |
| `llm_latency_ms` | время вызова модели |
| `tool_call_errors_total` | ошибки tool layer |
| `fallback_triggered_total` | срабатывания fallback |
| `session_completion_total` | завершенные сессии по статусам |
| `voice_board_desync_total` | рассинхрон голоса и доски |

---

## Langfuse traces

В `Langfuse` стоит логировать:

- input/output модели;
- версию system prompt;
- retrieval payload;
- review decision;
- fallback reason;
- итоговый tutoring status.

---

## Логи

Минимальный набор событий:

- request received;
- retrieval result;
- plan built;
- tool call;
- understanding check;
- fallback triggered;
- error.

Не логировать:

- лишние персональные данные;
- полные аудиозаписи по умолчанию;
- ключи и секреты.

---

## Offline evals

### Retrieval

- `precision@3`
- `recall@10`
- `nDCG@3`

### Tutor quality

- `tutor_explanation_score`
- `tutor_approval_rate`
- `llm_judge_score`
- `judge_human_agreement`

### Product quality

- `task_resolution_rate`
- `reexplanation_success_rate`
- `voice_board_sync_success_rate`
