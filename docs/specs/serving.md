# Serving / Config

## Базовый стек

Для первой версии достаточно такого разбиения:

- `OpenRouter` как основной gateway для control/review моделей;
- `Retriever service` для dense + lexical retrieval;
- `Voice runtime` для realtime speech-to-speech;
- `Redis` для session memory;
- `Langfuse` для traces и eval traces.

---

## Модели

| Роль | Вариант |
|---|---|
| Control model | модель через OpenRouter |
| Review model | более сильная reasoning model при необходимости |
| Embedding | `BAAI/bge-m3` |
| Reranker | `BAAI/bge-reranker-v2-m3` |
| STT fallback | `faster-whisper` |
| TTS fallback | `Silero TTS` или облачный low-latency provider |
| Realtime voice model | speech-capable realtime provider |

---

## Voice runtime

| Режим | Назначение |
|---|---|
| `realtime` | основной разговорный режим |
| `chained` | fallback при сбое realtime транспорта |

---

## Запуск

### LLM runtime

Используется OpenRouter или локальный совместимый runtime.

### Retrieval service

```bash
uvicorn services.retrieval:app --host 0.0.0.0 --port 8002
```

### Основное приложение

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Конфигурация

| Переменная | Описание |
|---|---|
| `LLM_BASE_URL` | URL LLM gateway |
| `OPENROUTER_API_KEY` | API key |
| `LLM_MODEL` | control model |
| `REVIEW_MODEL` | review model |
| `VOICE_MODE` | `realtime` / `chained` |
| `TTS_PROVIDER` | TTS backend |
| `ASR_ENABLED` | включить ASR fallback |
| `REDIS_URL` | memory store |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key |
| `LANGFUSE_HOST` | URL Langfuse |

---

## Ограничения

- realtime voice — основной режим, но не единственный;
- chained mode нужен как operational fallback;
- локальные модели допустимы, но не обязательны для первой версии.
