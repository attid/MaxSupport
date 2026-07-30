# Архитектура MaxSupport

## Обзор

MaxSupport — один асинхронный процесс с двумя входными потоками:

```text
MAX long polling ─┐
                  ├─> SupportService ─> SQLite
Telegram polling ─┘         │
                            ├─> Telegram Bot API
                            └─> MAX API
```

Composition root находится в `src/main.py`. Он создаёт адаптеры, запускает
фоновые задачи и гарантированно закрывает HTTP-клиенты, Telegram session и
SQLAlchemy engine.

## Слои

### Domain — `src/domain`

Содержит типизированные сущности `User`, `Ticket`, `TicketMessage` и
`Attachment`. Не импортирует другие слои.

### Application — `src/application`

Содержит use cases, monitoring и порты внешних систем. Зависит только от
domain. `SupportService` не знает об aiogram, httpx или SQLAlchemy.

### Infrastructure — `src/infrastructure`

Реализует application-порты:

- `SQLiteRepository` — async SQLAlchemy и SQLite;
- `MaxSender` — MAX API через httpx;
- `BotSender` — Telegram Bot API через aiogram;
- `Settings` и настройка structlog.

### Interface — `src/interface`

Принимает внешние события:

- Telegram handlers и middleware;
- MAX polling и строгие Pydantic-схемы входящих updates.

## Dependency rules

Допустимое направление:

```text
domain <- application <- infrastructure
                     \--- interface
```

- `domain` не импортирует другие слои;
- `application` не импортирует `infrastructure` или `interface`;
- `infrastructure` и `interface` не импортируют друг друга;
- `src/main.py` является единственным composition root и может импортировать
  все слои.

Правила и циклы импортов проверяются `.linters/check_architecture.py`.

## Данные

SQLite содержит таблицы `users`, `tickets` и `message_mappings`. История
сообщений хранится JSON внутри тикета. Все datetime при чтении нормализуются в
UTC. Схема создаётся idempotent-вызовом `create_all`; отдельного migration
framework пока нет.

## Внешние контракты

- Telegram: aiogram 3, long polling, forum topics.
- MAX: собственный адаптер для `/me`, `/updates`, `/uploads`, `/messages`.
- MAX endpoint: `https://platform-api.max.ru`.

Изменение endpoint, сертификатов, payload или схемы БД требует отдельного ADR и
обновления тестов/документации.
