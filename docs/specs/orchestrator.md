# Orchestrator

## Роль

`Tutor Orchestrator` — центральный модуль системы. Он управляет tutoring loop от входящего запроса до завершения сессии, выбирает стратегию объяснения, вызывает retrieval и инструменты, обновляет состояние сессии и следит за соблюдением policy.

---

## Шаги выполнения

```text
1. receive_input(user_msg, session_id, canvas_state)
2. sanitize_and_normalize(user_msg)
3. analyze_problem(...)                 # тема, сложность, confidence
4. if confidence < threshold:
       return clarification_question()
5. tasks = retrieve_tasks(...)
6. plan = build_pedagogical_plan(tasks, memory, canvas_state)
7. step_package = build_step_package(plan.current_step)
8. reviewed = review_step(step_package)
9. if review failed:
       reviewed = safe_minimal_hint()
10. deliver(reviewed.canvas_actions, reviewed.spoken_hint)
11. wait_for_student_signal()
12. assess_understanding(...)
13. if understood:
       advance_step_or_finish()
14. else:
       replan_with_more_support()
15. update_memory(...)
16. return current_status
```

---

## Правила переходов

| Состояние | Условие | Переход |
|---|---|---|
| problem analysis | confidence < 0.6 | → clarification |
| clarification | ученик уточнил условие | → problem analysis |
| retrieval | 0 результатов | → clarification или low-confidence hint |
| review | policy violation / invalid action | → safe minimal hint |
| understanding check | понял шаг | → next step |
| understanding check | не понял | → simpler retry |
| simpler retry | misunderstanding_count >= 3 | → short fallback / escalate |
| delivery | TTS failed | → text + canvas mode |
| delivery | canvas failed | → voice + text mode |
| memory update | store failed | → stateless continue |

---

## Stop Conditions

| Условие | Действие |
|---|---|
| Задача завершена | Сформировать финальный ответ и итог для родителя |
| Clarification pending | Остановить loop и ждать уточнение |
| 3 повторных объяснения без прогресса | Завершить с коротким fallback и рекомендацией взрослой помощи |
| Системная ошибка без безопасного fallback | Вернуть краткое сообщение об ошибке и сохранить статус |

---

## Retry / Fallback

| Компонент | Retry | Fallback |
|---|---|---|
| Problem analysis LLM | 1 retry | Перейти к clarification |
| Retrieval | нет | Короткая low-confidence hint |
| Planning | 1 retry | Упростить prompt и собрать minimal plan |
| Review | нет | Safe minimal hint без сложных canvas actions |
| TTS | 1 retry | Text-only response |
| Canvas dispatch | нет | Не выполнять action, оставить только hint text |

---

## Режимы tutoring

| Режим | Когда используется |
|---|---|
| `hint_first` | Базовый режим для первого шага |
| `scaffolded_step` | Когда ученик делает часть решения сам |
| `worked_example_light` | Когда нужен небольшой похожий пример |
| `re_explain_simpler` | После сигнала "не понял" |
| `short_fallback` | При repeated failure или деградации системы |

---

## Guardrails агента

| Guardrail | Реализация |
|---|---|
| Не решать за ученика сразу | Первые ответы строятся как подсказка, а не финальное решение |
| Ограничение инструментов | Агент может вызывать только разрешенные действия |
| Step schema | Каждый шаг обязан иметь `goal`, `spoken_hint`, `canvas_actions`, `check_question` |
| Max clarification turns | Не более 2 подряд вопросов на уточнение |
| Max re-explanations | Не более 3 подряд повторных объяснений |
