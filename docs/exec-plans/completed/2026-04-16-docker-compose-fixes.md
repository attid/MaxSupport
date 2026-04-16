# Docker Compose — переход на GHCR образ и исправление конфигурации

## Контекст
docker-compose.yml использовал `build: .`, bind mount и неправильные имена переменных окружения.

## План изменений
1. [x] `build: .` → `image: ghcr.io/attid/maxsupport:latest`
2. [x] `./data:/app/data` → именованный volume `data:/app/data`
3. [x] `BOT_TOKEN` → `TELEGRAM_BOT_TOKEN` (соответствие Settings)
4. [x] Добавлен `MAX_BOT_TOKEN` (отсутствовал)
5. [x] Добавлен `TELEGRAM_API_URL` с дефолтом
6. [x] Синхронизирован README с актуальными именами переменных

## Коммиты
- `5cd0fb4` fix(docker): use GHCR image, named volume and add missing MAX_BOT_TOKEN
- `7c748e0` style: format use_cases.py
- `29fd84f` feat: add configurable TELEGRAM_API_URL for custom TG API server
- `3309842` fix: use TelegramAPIServer.from_base() for custom API URL
