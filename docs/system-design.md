# System Design — Visual Voice Tutor Agent

## Референсы

Слой работы с холстом опирается на официальные материалы `tldraw`:

- [AI integrations](https://tldraw.dev/docs/ai)
- [Agent starter kit](https://tldraw.dev/starter-kits/agent)

Ключевые идеи оттуда:

- программный вызов агента из UI;
- двойной контекст холста: screenshot + structured shape data;
- типизированные действия агента с валидацией перед применением.

---

## 1. Ключевые архитектурные решения

| Решение | Обоснование |
|---|---|
| Детерминированный tutoring loop | Вместо свободного agent loop система идет по стадиям: анализ, retrieval, план, проверка, показ шага |
| `tldraw` как основной интерфейс | Агент объясняет не только текстом, а через заметки, стрелки, таблицы и подсветку |
| Realtime speech-to-speech как основной voice path | Взаимодействие должно ощущаться живым; chained voice path остается fallback-режимом |
| Банк задач как внешняя база знаний | Retrieval опирается на задачи с метаданными, шагами решения и уровнями подсказок |
| Hybrid retrieval | Для математики важны и смысл, и точное совпадение формулировок |
| Review перед показом шага | Перед delivery система проверяет policy, схему ответа и canvas actions |
| Stateful session memory | Система помнит ход текущей сессии и повторяющиеся затруднения |
| Явные fallback-режимы | При сбое voice, canvas, retrieval или memory сессия должна продолжаться в упрощенном виде |

---

## 2. Модули и их роли

| Модуль | Роль |
|---|---|
| **Student UI / tldraw Frontend** | Холст, кнопки действий, отображение визуальных подсказок |
| **Canvas Context Builder** | Собирает screenshot, shapes in view, selection и recent actions |
| **Tutor Orchestrator** | Управляет tutoring loop, вызывает retrieval и инструменты |
| **Task Retriever** | Ищет релевантные задачи в банке задач |
| **Pedagogical Planner** | Превращает retrieved context в пошаговый план объяснения |
| **Canvas Action Executor** | Применяет безопасные действия к `tldraw` |
| **Voice Layer** | Основной режим — realtime voice, резервный — chained voice |
| **Session Memory Store** | Хранит состояние сессии и краткий профиль ученика |
| **Validator / Guardrails** | Следит за hint-first policy и валидирует output |
| **Observability / Evals** | Langfuse, application metrics, offline evals |

---

## 3. Основной workflow

```text
1. Student input
2. Canvas context build
3. Problem analysis
4. Low confidence? -> clarification
5. Task retrieval
6. Pedagogical planning
7. Step package build
8. Review / validation
9. Delivery: board + realtime voice
10. Understanding check
11. Simpler retry or next step
12. Memory update
13. Parent summary
```

---

## 4. State / Memory / Context

### Session State

- `session_id`
- `dialog_history`
- `current_problem`
- `retrieved_tasks`
- `current_plan`
- `current_step_idx`
- `misunderstanding_count`
- `canvas_snapshot_ref`
- `completion_status`

### Long-term Memory

Для первой версии достаточно хранить:

- класс ученика;
- последние проблемные темы;
- повторяющиеся ошибки;
- короткие итоги сессий.

### Context Budget

| Слот | Лимит |
|---|---|
| System + policy prompt | ~1200 токенов |
| Student profile | ≤500 |
| Session history | ≤1200 |
| Retrieved tasks | ≤1800 |
| Canvas summary | ≤600 |
| User message | ≤400 |

При переполнении:

- history summarization;
- сокращение retrieval до top-2;
- упрощение canvas summary.

---

## 5. Retrieval-контур

Источник данных — **банк задач**.

Каждая запись:

- `task_id`
- `grade`
- `topic`
- `difficulty`
- `problem_text`
- `solution_steps`
- `hint_levels`
- `board_pattern`

Pipeline:

```text
problem
→ normalize
→ dense retrieval
→ lexical retrieval
→ fusion
→ rerank
→ top-3 tasks
```

Параметры:

- dense: `BAAI/bge-m3`
- lexical: BM25 / FTS
- reranker: `BAAI/bge-reranker-v2-m3`

---

## 6. Tools / API интеграции

### Canvas

Разрешенные high-level actions:

- `highlight_area`
- `place_hint_note`
- `draw_arrow`
- `draw_number_line`
- `draw_place_value_table`
- `reveal_next_step`

### Voice

- основной режим: realtime speech-to-speech;
- fallback: chained `ASR → text → TTS`;
- при полном сбое voice слой отключается, сессия продолжается через text + canvas.

### Programmatic trigger

Для tutor-сценария агент вызывается из UI-кнопок, а не только из чата:

- `Review Work`
- `Explain Step`
- `Give Hint`
- `Check Understanding`

---

## 7. Failure Modes и Guardrails

| Компонент | Failure | Fallback |
|---|---|---|
| LLM | timeout / 5xx | retry, затем короткая текстовая подсказка |
| Retrieval | 0 результатов | clarification или low-confidence hint |
| Realtime voice | transport error | chained mode |
| Voice layer | недоступен | text + canvas |
| Canvas executor | action error | voice/text without board step |
| Memory store | недоступен | stateless mode |

Guardrails:

- hint-first policy;
- anti-cheating;
- age adaptation;
- ограниченный набор canvas actions;
- schema validation для step package.

---

## 8. Ограничения

### Latency

- time to first visible response: идеальная цель `< 1 с`, допустимый компромисс `p95 < 5 с`
- end-to-end step delivery: `p95 < 5 с`

### Cost

- обычно `1–2` LLM calls на шаг;
- `1` retrieval + rerank на шаг;
- realtime voice как основной режим, chained — только fallback.

### In scope

- математика для 4–7 класса;
- одна задача за сессию;
- realtime voice + `tldraw`;
- retrieval только по банку задач.

### Out of scope

- все школьные предметы;
- длинная образовательная траектория;
- general-purpose chat mode.
