# Max API — исправление поллинга и формата сообщений

## Контекст
Max API использует другой формат чем Telegram Bot API. Поллинг падал с пустой ошибкой.
Проверено с помощью живого API и документации dev.max.ru.

## План изменений
1. [x] `GET /updates`: `offset` → `marker`, `results` → `updates`
2. [x] Формат update: `message.from` → `message.sender`, `message.text` → `message.body.text`
3. [x] Фильтрация по `update_type == "message_created"`
4. [x] `POST /messages`: `chat_id` как query-параметр, не JSON body
5. [x] Сохранение `max_chat_id` из `message.recipient.chat_id` в тикете
6. [x] httpx timeout увеличен до 60с (long polling 30с)
7. [x] Обновлены тесты и интерфейсы

## Верификация
- Протестировано с живым Max API через test_max_api.py скрипт
- Подтверждена структура: `sender.user_id`, `body.text`, `recipient.chat_id`
- `POST /messages` работает с `params={"chat_id": ...}`, JSON body — 400

## Коммиты
- `73eb4e8` fix(max): align polling with Max API — use marker, sender, body.text
- `3a904ba` fix(max): use chat_id from incoming message for sending replies
- `74f789c` fix(max): pass chat_id as query param, not JSON body
