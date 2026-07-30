# MaxSupport

MaxSupport связывает клиентский бот MAX с форум-группой ассистентов в
Telegram. Каждое обращение становится отдельным Telegram topic, а сообщения и
вложения пересылаются в обе стороны.

## Как работает

1. `MaxPollingService` получает сообщение клиента через long polling.
2. `SupportService` создаёт пользователя, тикет и Telegram forum topic.
3. Ассистент берёт тикет, отвечает и закрывает его кнопками в topic.
4. Ответы и вложения отправляются клиенту через MAX API.
5. `AlarmService` сообщает о вопросах без ответа более двух часов в рабочее
   время.

## Требования

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- [just](https://github.com/casey/just)
- Telegram forum group, где бот имеет права управлять topics

## Локальный запуск

```bash
uv sync --frozen
just check

TELEGRAM_BOT_TOKEN=change_me \
MAX_BOT_TOKEN=change_me \
ASSISTANTS_CHAT_ID=-1000000000000 \
just run
```

Для локальных человекочитаемых логов добавьте `LOG_FORMAT=console`. По
умолчанию приложение пишет JSON.

## Docker Compose

В [`docker-compose.yml`](docker-compose.yml) замените literal placeholders
`change_me` и пример `ASSISTANTS_CHAT_ID` непосредственно в интерфейсе
управления Compose, затем запустите сервис. Дополнительные sidecar-файлы не
требуются.

```bash
docker compose up -d
```

Данные SQLite хранятся в именованном volume `data`.

## Команды

| Команда | Назначение |
|---|---|
| `just run` | Запустить сервис |
| `just test` | Полный набор тестов |
| `just test-fast` | Краткий вывод быстрого набора |
| `just lint` | Ruff и Pyright |
| `just fmt` | Исправить lint/format автоматически |
| `just fmt-check` | Проверить формат без изменений |
| `just arch-test` | Проверить слои и циклы импортов |
| `just metrics` | Вывести JSON-метрики размера кода |
| `just check` | Полная немутирующая проверка перед PR |

## Конфигурация

| Переменная | Обязательность | Значение |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | да | Токен Telegram-бота |
| `MAX_BOT_TOKEN` | да | Токен MAX-бота |
| `ASSISTANTS_CHAT_ID` | да | ID Telegram forum group |
| `DB_URL` | нет | `sqlite+aiosqlite:///./data.db` |
| `TELEGRAM_API_URL` | нет | Base URL custom API server; пустое значение использует `https://api.telegram.org` |
| `LOG_FORMAT` | нет | `json` или `console` |

MAX используется через собственный адаптер `httpx`. Endpoint остаётся
`https://platform-api.max.ru`.

Например, `TELEGRAM_API_URL=https://api.mtlminiapps.us` переключает aiogram на
`https://api.mtlminiapps.us/bot{token}/{method}` и
`https://api.mtlminiapps.us/file/bot{token}/{path}`.

## Документация

- [Архитектура](docs/architecture.md)
- [Конвенции](docs/conventions.md)
- [Золотые принципы](docs/golden-principles.md)
- [Глоссарий](docs/glossary.md)
- [Оценки качества](docs/quality-grades.md)
- [Локальная проверка](docs/runbooks/local-verification.md)
