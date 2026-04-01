# Memory / Context

## Session State

Каждая сессия идентифицируется через `session_id`. Состояние хранится в Redis или совместимом in-memory KV-store.

```python
SessionState = {
    "session_id": str,
    "student_id": str | None,
    "grade_band": str,
    "dialog_history": list,
    "current_problem": dict | None,
    "retrieved_tasks": list,
    "current_plan": list,
    "current_step_idx": int,
    "misunderstanding_count": int,
    "clarification_pending": bool,
    "canvas_snapshot_ref": str | None,
    "viewport_summary": dict | None,
    "focused_shape_ids": list[str],
    "last_canvas_actions": list,
    "last_spoken_hint": str | None,
    "completion_status": str | None,
}
```

---

## Long-term Student Memory

Долгосрочная память в первой версии минимальна:

| Поле | Описание |
|---|---|
| `grade_band` | Класс / возрастная группа |
| `recent_topics` | Последние разобранные темы |
| `weak_spots` | Повторяющиеся затруднения |
| `preferred_pace` | Быстро / нейтрально / медленно |
| `session_summaries` | Короткие итоги прошлых сессий |

---

## Memory Policy

| Тип данных | TTL | При истечении |
|---|---|---|
| Dialog history | 60 мин | Удаление |
| Current problem / current plan | 60 мин | Удаление |
| Weak spots | 30 дней | Пересчет / удаление |
| Parent summary | 30 дней | Удаление |
| Raw audio | ≤ 24 ч или не хранить вовсе | Удаление |

---

## Context Budget

| Слот | Лимит | Приоритет при переполнении |
|---|---|---|
| System + policy prompt | 1200 токенов | Не обрезается |
| Student profile summary | 500 токенов | Сжимается |
| Session history | 1200 токенов | Обрезается oldest-first |
| Retrieved tasks | 1800 токенов | Уменьшить `top_n` |
| Canvas summary | 600 токенов | Свернуть до компактного описания |
| User input | 400 токенов | Нормализация / усечение |
| **Итого** | **≤5700 токенов** | |

### Summarization

Если session history выходит за лимит:

- вызвать отдельный summarizer;
- заменить старые turn-ы кратким summary;
- сохранить отдельно raw history в storage до истечения TTL.

---

## Context Assembly

```python
def build_context(session, retrieved_tasks, canvas_summary, user_msg):
    return {
        "system": SYSTEM_AND_POLICY_PROMPTS,
        "student_profile": summarize_profile(session),
        "history": truncate_history(session["dialog_history"]),
        "retrieval": format_tasks(retrieved_tasks[:3]),
        "canvas": compact_canvas_summary(canvas_summary),
        "user": normalize(user_msg),
    }
```

---

## Ограничения

- Memory не должна превращаться в бесконтрольное хранилище всех данных ребенка;
- Long-term memory в первой версии ограничена и не претендует на полный learner model;
- При недоступности storage система должна продолжать в stateless режиме.
