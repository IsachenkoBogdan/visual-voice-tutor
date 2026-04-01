# Retriever

## Назначение

`Task Retriever` ищет в банке задач записи, похожие на текущую задачу ученика, и возвращает опорные материалы для шага объяснения: формулировку, шаги решения, уровни подсказок и метаданные.

---

## Источник данных

В первой версии используется только **банк задач**.

Минимальная структура записи:

| Поле | Описание |
|---|---|
| `task_id` | Уникальный идентификатор |
| `grade` | Класс: 4, 5, 6, 7 |
| `topic` | Тема: дроби, уравнения, проценты и т.п. |
| `subtopic` | Более узкий раздел |
| `difficulty` | Easy / Medium / Hard |
| `problem_text` | Текст задачи |
| `final_answer` | Итоговый ответ |
| `solution_steps` | Канонические шаги решения |
| `hint_levels` | 1–3 уровня подсказок |
| `board_pattern` | Предпочтительный тип визуализации |
| `tags` | Дополнительные метки |

---

## Индекс

| Параметр | Значение |
|---|---|
| Embedding model | `BAAI/bge-m3` |
| Dense index | FAISS `IVFFlat` или HNSW |
| Lexical index | BM25 / Postgres FTS / Tantivy |
| Merge | Reciprocal Rank Fusion |
| Similarity metric | cosine similarity |
| Indexed text | `topic + subtopic + problem_text + condensed_solution_summary` |
| Update policy | offline batch |

---

## Search

```python
def retrieve_tasks(query: str, grade: int | None, topic: str | None, top_k: int = 15):
    normalized = normalize_problem(query)
    filters = build_filters(grade=grade, topic=topic)
    dense_hits = vector_search(normalized, top_k=20, filters=filters)
    lexical_hits = lexical_search(normalized, top_k=20, filters=filters)
    merged = fuse_ranks(dense_hits, lexical_hits)
    reranked = rerank(normalized, merged[:10])
    return reranked[:3]
```

### Параметры поиска

| Параметр | Значение |
|---|---|
| dense top_k | 20 |
| lexical top_k | 20 |
| fusion cut | 10 |
| top_n после reranking | 3 |
| Min similarity threshold | 0.30 |
| Pre-filter | `grade`, `topic`, `difficulty` если уверенно извлечены |

---

## Reranking

| Параметр | Значение |
|---|---|
| Model | `BAAI/bge-reranker-v2-m3` |
| Input | query + task text / short solution summary |
| Выход | relevance score |
| Fallback | При exception вернуть dense order |

---

## Что retrieval возвращает planner-у

```python
RetrievedTask = {
    "task_id": str,
    "problem_text": str,
    "topic": str,
    "grade": int,
    "difficulty": str,
    "solution_steps": list[str],
    "hint_levels": list[str],
    "board_pattern": str,
    "score": float,
}
```

Planner не обязан показывать найденную задачу ученику напрямую. Retrieval нужен как опора для следующего шага объяснения.

---

## Ограничения

- Retrieval покрывает только темы, которые реально есть в банке задач;
- составные и плохо сформулированные задачи все равно могут давать слабые совпадения;
- если у задач плохие step annotations, качество tutoring заметно падает;
- банк задач решает задачу первой версии, но не заменяет полноценную учебную базу.
