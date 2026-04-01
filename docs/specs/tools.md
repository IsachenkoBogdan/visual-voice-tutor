# Tools / APIs

## Tool Layer

Инструменты вызываются через единый `ToolDispatcher`, который:

- принимает уже готовый step package;
- проверяет, что действие входит в разрешенный набор;
- валидирует payload;
- применяет timeout и fallback.

---

## Canvas Tool (`tldraw`)

Агент работает не с raw mutations, а с high-level actions.

Разрешенные действия:

- `highlight_area`
- `place_hint_note`
- `draw_arrow`
- `draw_number_line`
- `draw_place_value_table`
- `reveal_next_step`
- `clear_last_agent_overlay`

Перед вызовом действий в модель уходит:

- screenshot viewport;
- описание фигур в кадре;
- selection;
- recent actions.

### Ошибки / fallback

| Ошибка | Реакция |
|---|---|
| invalid payload | не выполнять action |
| anchor not found | разместить note в safe default zone |
| execution timeout | пропустить визуальный шаг |

---

## Voice Layer

### Основной режим

- realtime speech-to-speech;
- tutor orchestrator остается главным reasoning backend.

### Резервный режим

- chained path: `ASR → text → TTS`.

### Fallback

- если voice недоступен, система работает в `text + canvas` режиме.

---

## Optional ASR

| Условие | Реакция |
|---|---|
| confidence >= 0.75 | использовать как input |
| 0.5 <= confidence < 0.75 | запросить подтверждение |
| confidence < 0.5 | text fallback |

---

## Parent Summary

В первой версии это внутренний formatter, не внешний API.

---

## Защита Tool Layer

| Мера | Реализация |
|---|---|
| Ограничение инструментов | Только заранее описанные canvas actions и voice calls |
| Schema validation | Проверка payload до исполнения |
| Timeouts | На каждом интеграционном вызове |
| No dangerous side effects | Нет необратимых внешних действий |
