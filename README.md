# MaxSupport

Система поддержки клиентов через Telegram и Max API. Клиенты пишут в чат-бот Max, ассистенты отвечают через форум-группу Telegram.

## Архитектура

Чистая архитектура с 4 слоями: `domain → application → infrastructure / interface`. Подробности — в [`docs/architecture.md`](docs/architecture.md).

## Быстрый старт

### Требования

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

### Локальная разработка

```bash
# Установить зависимости
uv sync

# Создать .env файл
cp .env.example .env
# Заполнить BOT_TOKEN, MAX_BOT_TOKEN, ASSISTANTS_CHAT_ID

# Запустить тесты
just test

# Запустить бота
PYTHONPATH=. uv run python -m src.main
```

### Docker

```bash
docker compose up -d
```

## Команды

| Команда | Назначение |
|---------|-----------|
| `just test` | Запустить тесты |
| `just lint` | Линтинг (ruff check) |
| `just fmt` | Автоформатирование |
| `just check` | `fmt + lint + test` — полная проверка |

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `BOT_TOKEN` | Токен Telegram бота |
| `MAX_BOT_TOKEN` | Токен Max бота |
| `ASSISTANTS_CHAT_ID` | ID форум-группы ассистентов |
| `DB_URL` | URL базы данных (default: `sqlite+aiosqlite:///./data.db`) |

## Как работает

1. Клиент пишет боту в Max → `MaxPollingService` получает обновление
2. Создаётся тикет + форум-топик 🔴 в группе ассистентов
3. Ассистент нажимает «Взять» → топик становится 🟡
4. Переписка пересылается между Max и Telegram
5. Ассистент нажимает «Закрыть» → топик 🟢, клиент уведомлён
6. Если нет ответа >2ч в рабочее время — аларм в топик
